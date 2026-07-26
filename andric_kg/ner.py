from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional

from .dates import find_date_spans
from .utils import canonical_label, dedupe_dicts


@dataclass
class EntityMention:
    letter_id: str
    text: str
    label: str
    start: Optional[int]
    end: Optional[int]
    score: Optional[float]
    model: str


HF_LABEL_MAP = {
    "PER": "PER",
    "PERSON": "PER",
    "LOC": "LOC",
    "LOCATION": "LOC",
    "ORG": "ORG",
    "ORGANIZATION": "ORG",
    "MISC": "MISC",
}

GLINER_LABEL_MAP = {
    "person": "PER",
    "location": "LOC",
    "organization": "ORG",
    "publication": "PUBLICATION",
    "periodical": "PUBLICATION",
    "literary work": "WORK",
}


def _hf_raw_label(result: Dict[str, Any]) -> str:
    """Return a comparable label from a Transformers pipeline result."""
    return str(result.get("entity_group") or result.get("entity") or "MISC").upper()


def _merge_hf_wordpieces(results: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge adjacent WordPiece continuations emitted as separate NER results.

    A WordPiece token prefixed with ``##`` continues the preceding token without
    a space. Some token-classification models assign a new B-* tag to each piece,
    so Transformers' ``aggregation_strategy="simple"`` can leave those pieces as
    separate entities. Offsets are supplied by the pipeline; callers do not need
    to calculate them.
    """
    merged: List[Dict[str, Any]] = []

    for result in results:
        current = dict(result)
        raw_word = str(current.get("word") or "")

        if merged:
            previous = merged[-1]
            previous_end = previous.get("end")
            current_start = current.get("start")
            same_label = _hf_raw_label(previous) == _hf_raw_label(current)
            is_continuation = raw_word.lstrip().startswith("##")
            contiguous = (
                isinstance(previous_end, int)
                and isinstance(current_start, int)
                and previous_end == current_start
            )

            if same_label and is_continuation and contiguous:
                previous["word"] = str(previous.get("word") or "") + raw_word.lstrip()
                previous["end"] = current.get("end", previous_end)
                previous["score"] = min(
                    float(previous.get("score", 0.0)),
                    float(current.get("score", 0.0)),
                )
                continue

        merged.append(current)

    return merged


def _hf_entity_text(text: str, result: Dict[str, Any]) -> str:
    """Recover an entity's surface form, preferring the original source text."""
    start = result.get("start")
    end = result.get("end")
    if (
        isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start < end <= len(text)
    ):
        return canonical_label(text[start:end])

    # Defensive fallback for tokenizers/pipelines that do not provide offsets.
    word = str(result.get("word") or "")
    return canonical_label(word.replace(" ##", "").replace("##", ""))


class HuggingFaceNER:
    def __init__(self, model_name: str, min_score: float = 0.60):
        from transformers import pipeline

        self.model_name = model_name
        self.min_score = min_score
        self.pipe = pipeline(
            "token-classification",
            model=model_name,
            aggregation_strategy="simple",
        )

    def extract(self, text: str, letter_id: str) -> List[EntityMention]:
        results = _merge_hf_wordpieces(self.pipe(text))
        mentions: List[EntityMention] = []
        for r in results:
            score = float(r.get("score", 0.0))
            if score < self.min_score:
                continue
            raw_label = _hf_raw_label(r)
            label = HF_LABEL_MAP.get(raw_label.upper(), raw_label.upper())
            ent_text = _hf_entity_text(text, r)
            if not ent_text or len(ent_text) < 2:
                continue
            mentions.append(
                EntityMention(
                    letter_id=letter_id,
                    text=ent_text,
                    label=label,
                    start=r.get("start"),
                    end=r.get("end"),
                    score=score,
                    model=self.model_name,
                )
            )
        return mentions


class GlinerNER:
    def __init__(self, model_name: str, labels: List[str], threshold: float = 0.35):
        from gliner import GLiNER

        self.model_name = model_name
        self.labels = labels
        self.threshold = threshold
        self.model = GLiNER.from_pretrained(model_name)

    def extract(self, text: str, letter_id: str) -> List[EntityMention]:
        results = self.model.predict_entities(text, self.labels, threshold=self.threshold)
        mentions: List[EntityMention] = []
        for r in results:
            raw_label = str(r.get("label", "")).lower()
            label = GLINER_LABEL_MAP.get(raw_label, raw_label.upper())
            ent_text = canonical_label(str(r.get("text") or ""))
            if not ent_text or len(ent_text) < 2:
                continue
            mentions.append(
                EntityMention(
                    letter_id=letter_id,
                    text=ent_text,
                    label=label,
                    start=r.get("start"),
                    end=r.get("end"),
                    score=float(r.get("score", 0.0)) if r.get("score") is not None else None,
                    model=self.model_name,
                )
            )
        return mentions


def extract_date_mentions(text: str, letter_id: str) -> List[EntityMention]:
    """Extract dates with deterministic rules as a complement to ML NER."""
    mentions: List[EntityMention] = []
    for start, end in find_date_spans(text):
        mentions.append(
            EntityMention(
                letter_id=letter_id,
                text=canonical_label(text[start:end]),
                label="DATE",
                start=start,
                end=end,
                score=1.0,
                # The CSV schema calls this field "model", but this value is
                # provenance for a deterministic extractor, not an ML model.
                model="rule-based-date-v1",
            )
        )
    return mentions


def run_ner_for_letters(letters: Iterable[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    ner_cfg = config.get("ner", {})
    hf_model = ner_cfg.get("hf_model", "classla/bcms-bertic-ner")
    min_score = float(ner_cfg.get("min_score", 0.60))
    use_gliner = bool(ner_cfg.get("use_gliner", False)) or os.getenv("USE_GLINER") == "1"

    hf = HuggingFaceNER(hf_model, min_score=min_score)
    gliner = None
    if use_gliner:
        try:
            gliner = GlinerNER(
                ner_cfg.get("gliner_model", "urchade/gliner_large-v2"),
                labels=ner_cfg.get("gliner_labels", ["person", "location", "organization", "publication", "literary work"]),
                threshold=float(ner_cfg.get("gliner_threshold", 0.35)),
            )
        except Exception as exc:
            print(f"WARNING: GLiNER not available or failed to load: {exc}")

    all_mentions: List[EntityMention] = []
    for letter in letters:
        letter_id = letter["letter_id"]
        text = letter.get("text", "")
        print(f"NER: {letter_id}")
        all_mentions.extend(hf.extract(text, letter_id))
        all_mentions.extend(extract_date_mentions(text, letter_id))
        if gliner:
            all_mentions.extend(gliner.extract(text, letter_id))

    rows = [asdict(m) for m in all_mentions]
    return dedupe_dicts(rows, key_fields=["letter_id", "text", "label", "start", "end"])

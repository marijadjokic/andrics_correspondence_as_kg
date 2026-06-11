from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional

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
        results = self.pipe(text)
        mentions: List[EntityMention] = []
        for r in results:
            score = float(r.get("score", 0.0))
            if score < self.min_score:
                continue
            raw_label = str(r.get("entity_group") or r.get("entity") or "MISC")
            label = HF_LABEL_MAP.get(raw_label.upper(), raw_label.upper())
            ent_text = canonical_label(str(r.get("word") or ""))
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
    """Simple backup date extractor, because many NER models miss historical/abbreviated dates."""
    patterns = [
        r"\b\d{1,2}\s*\.\s*(?:[IVXLCDM]+|\d{1,2})\s*\.\s*\d{2,4}\b",
        r"\b\d{1,2}\s+(?:januar|februar|mart|april|maj|jun|jul|avgust|septembar|oktobar|novembar|decembar)[a-z]*\s+\d{2,4}\b",
        r"\b\d{4}\b",
    ]
    mentions: List[EntityMention] = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            mentions.append(
                EntityMention(
                    letter_id=letter_id,
                    text=canonical_label(m.group(0)),
                    label="DATE",
                    start=m.start(),
                    end=m.end(),
                    score=1.0,
                    model="regex-date",
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

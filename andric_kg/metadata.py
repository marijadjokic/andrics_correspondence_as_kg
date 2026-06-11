from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from .dates import extract_place_and_date
from .utils import canonical_label


GREETING_RE = re.compile(r"(?im)^\s*(Dragi|Draga|Poštovani|Poštovana)\s+(.+?)[,!]?$", re.U)
ADDRESS_MARKER_RE = re.compile(r"(?i)\[?\s*adresa\s*:?\s*\]?")


def infer_sender(text: str, default_sender: str = "Ivo Andrić") -> str:
    # In this corpus, Andrić is the author of the selected letters. Keep this explicit as corpus metadata.
    return default_sender


def infer_recipient_from_address(text: str, mentions: List[Dict[str, Any]]) -> Optional[str]:
    lines = text.splitlines()
    address_start_idx = None
    for i, line in enumerate(lines):
        if ADDRESS_MARKER_RE.search(line):
            address_start_idx = i
            break
    if address_start_idx is None:
        return None

    address_block = "\n".join(lines[address_start_idx: address_start_idx + 8])
    per_mentions = [m for m in mentions if m.get("label") == "PER" and m.get("text") in address_block]
    if per_mentions:
        # Prefer longest name in address block.
        return sorted([m["text"] for m in per_mentions], key=len, reverse=True)[0]

    # Backup: often the address starts with Dr. Name Surname.
    m = re.search(r"(?:Dr\.?|Gospodica|Gospođa|Gospoda)?\s*([A-ZČĆŽŠĐ][\wčćžšđČĆŽŠĐ]+\s+[A-ZČĆŽŠĐ][\wčćžšđČĆŽŠĐ]+)", address_block)
    if m:
        return canonical_label(m.group(1))
    return None


def infer_recipient_from_greeting(text: str, mentions: List[Dict[str, Any]]) -> Optional[str]:
    head = "\n".join(text.splitlines()[:12])
    m = GREETING_RE.search(head)
    if not m:
        return None
    greeting_tail = canonical_label(m.group(2))
    # If the greeting contains a real name, use it.
    if len(greeting_tail.split()) >= 2 and not re.search(r"gospodic|gospodj|prijatelj|vojko", greeting_tail, re.I):
        return greeting_tail
    # Otherwise check if a person is very near the greeting.
    for ent in mentions:
        if ent.get("label") == "PER" and ent.get("start") is not None and int(ent["start"]) < 300:
            return ent["text"]
    return None


def enrich_letters_with_metadata(
    letters: List[Dict[str, Any]],
    mentions: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    extraction_cfg = config.get("extraction", {})
    default_sender = extraction_cfg.get("default_sender", "Ivo Andrić")
    default_recipient = extraction_cfg.get("default_recipient", "")

    mentions_by_letter: Dict[str, List[Dict[str, Any]]] = {}
    for m in mentions:
        mentions_by_letter.setdefault(m["letter_id"], []).append(m)

    enriched: List[Dict[str, Any]] = []
    for letter in letters:
        text = letter.get("text", "")
        place, date_iso, matched_header = extract_place_and_date(text)
        lm = mentions_by_letter.get(letter["letter_id"], [])
        recipient = (
            infer_recipient_from_address(text, lm)
            or infer_recipient_from_greeting(text, lm)
            or default_recipient
            or ""
        )
        row = dict(letter)
        row.update(
            {
                "sender": infer_sender(text, default_sender=default_sender),
                "recipient": recipient,
                "date_iso": date_iso or "",
                "place_written": place or "",
                "date_header_match": matched_header or "",
            }
        )
        enriched.append(row)
    return enriched

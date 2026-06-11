from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml
from slugify import slugify


def dehyphenate_linebreaks(text: str) -> str:
    """
    Join words broken across line breaks by OCR / printed page layout.

    Examples:
    Polj-\nsku  -> Poljsku
    Pri-\npovetke -> Pripovetke
    Du-\nbrovnik -> Dubrovnik
    """
    if not text:
        return ""

    # Join words split by hyphen at the end of a line.
    text = re.sub(
        r"([A-Za-zÀ-žА-Яа-яЉЊЂЋЏљњђћџČĆŽŠĐčćžšđ])\s*[-‐-‒–—]\s*\n\s*([A-Za-zÀ-žА-Яа-яЉЊЂЋЏљњђћџČĆŽŠĐčćžšđ])",
        r"\1\2",
        text,
    )

    return text

def load_config(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_json(path: str | Path, data: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_text(text: str) -> str:
    """Normalize OCR/HTR text lightly without destroying historical spelling.

    This removes common OCR artefacts but keeps Serbian/Croatian diacritics and Cyrillic.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\ufeff", "")
    text = text.replace("￾", "")
    text = text.replace("­", "")  # soft hyphen rendered as visible char in some OCR outputs
    text = text.replace("\u00ad", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def canonical_label(label: str) -> str:
    label = normalize_text(label)
    label = re.sub(r"\s+", " ", label).strip(" ,.;:()[]{}\"'“”„")
    return label


def make_slug(label: str, prefix: str = "entity") -> str:
    s = slugify(label, lowercase=True, separator="_")
    if not s:
        s = "unknown"
    if s[0].isdigit():
        s = f"{prefix}_{s}"
    return s


def dedupe_dicts(items: Iterable[Dict[str, Any]], key_fields: List[str]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for item in items:
        key = tuple(item.get(k) for k in key_fields)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def load_manual_links(csv_path: str | Path) -> Dict[tuple[str, str], str]:
    path = Path(csv_path)
    if not path.exists():
        return {}
    links: Dict[tuple[str, str], str] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = canonical_label(row.get("label", ""))
            typ = (row.get("type", "") or "").upper()
            uri = (row.get("wikidata_uri", "") or "").strip()
            if label and typ and uri:
                links[(label.lower(), typ)] = uri
    return links

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from .utils import canonical_label, load_manual_links

WD_API = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": (
        "AndricLettersKG/0.1 "
        "(research project; contact: your.email@example.org)"
    ),
    "Accept": "application/json",
}


def wikidata_search(label: str, language: str = "sr", fallback_language: str = "en") -> Optional[str]:
    label = canonical_label(label)
    if not label:
        return None

    for lang in [language, fallback_language]:
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": lang,
            "uselang": lang,
            "search": label,
            "limit": 1,
        }
        try:
            r = requests.get(WD_API, params=params, headers=HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()
            results = data.get("search", [])
            if results:
                qid = results[0].get("id")
                if qid:
                    return f"http://www.wikidata.org/entity/{qid}"
        except Exception as exc:
            print(f"WARNING: Wikidata lookup failed for {label!r}: {exc}")
    return None


def build_entities_table(
    mentions: Iterable[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    linking_cfg = config.get("linking", {})
    manual_links = load_manual_links(linking_cfg.get("manual_links_csv", "data/config/manual_entity_links.csv"))
    enable_lookup = bool(linking_cfg.get("enable_wikidata_lookup", True))
    language = linking_cfg.get("wikidata_language", "sr")
    fallback = linking_cfg.get("fallback_language", "en")

    by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for m in mentions:
        label = canonical_label(m.get("text", ""))
        typ = (m.get("label", "MISC") or "MISC").upper()
        if not label:
            continue
        key = (label.lower(), typ)
        if key not in by_key:
            by_key[key] = {
                "entity_id": "",
                "label": label,
                "type": typ,
                "wikidata_uri": "",
                "mention_count": 0,
            }
        by_key[key]["mention_count"] += 1

    rows = []
    for (label_lower, typ), row in sorted(by_key.items(), key=lambda kv: (kv[1]["type"], kv[1]["label"])):
        label = row["label"]
        uri = manual_links.get((label.lower(), typ), "")
        if not uri and enable_lookup and typ in {"PER", "LOC", "ORG", "WORK", "PUBLICATION"}:
            uri = wikidata_search(label, language=language, fallback_language=fallback) or ""
            time.sleep(0.5) # be polite to Wikidata
        row["wikidata_uri"] = uri
        rows.append(row)
    return rows

#!/usr/bin/env python

import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd


LETTERS_CSV = PROJECT_ROOT / "data/output/letters.csv"
LETTERS_CSV_FIX = PROJECT_ROOT / "data/output/letters_fixed.csv"


PLACE_ALIASES = {
    "Сарајево": "Sarajevo",
    "Sarajevo": "Sarajevo",

    "Београд": "Beograd",
    "Beograd": "Beograd",

    "Атина": "Atina",
    "Atina": "Atina",

    "Вишеград": "Višegrad",
    "Višegrad": "Višegrad",

    "Марсеј": "Marseille",
    "Mарсеј": "Marseille",
    "Marseille": "Marseille",

    "Женева": "Ženeva",
    "Ženeva": "Ženeva",
    "Zeneva": "Ženeva",
    "Geneve": "Ženeva",

    "Берлин": "Berlin",
    "Berlin": "Berlin",

    "Mapcej": "Marseille",
    "Мapcej": "Marseille",
    "Mарсеј": "Marseille",
    "Марсеј": "Marseille",
    "Марсej": "Marseille",
}


PLACE_RE = re.compile(
    r"^(Сарајево|Sarajevo|Београд|Beograd|Атина|Atina|Вишеград|Višegrad|"
    r"Марсеј|Mарсеј|Marseille|Женева|Ženeva|Zeneva|Geneve|Берлин|Berlin)"
)


def infer_place_from_text(text: str) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None

    first_lines = [line.strip() for line in text.splitlines() if line.strip()][:4]

    for line in first_lines:
        m = PLACE_RE.search(line)
        if m:
            return PLACE_ALIASES.get(m.group(1), m.group(1))

    return None


def normalize_place(place: str | float | None, text: str) -> str | None:
    if isinstance(place, str) and place.strip() and place.strip() != "nan":
        place = place.strip()
        return PLACE_ALIASES.get(place, place)

    return infer_place_from_text(text)


def main():
    df = pd.read_csv(LETTERS_CSV, encoding="utf-8-sig")

    # In this selected corpus, all letters are from Ivo Andrić to Zdenka Marković.
    # This is metadata normalization, not manual NER extraction.
    df["sender"] = "Ivo Andrić"
    df["recipient"] = "Zdenka Marković"

    df["place_written"] = df.apply(
        lambda row: normalize_place(row.get("place_written"), row.get("text", "")),
        axis=1,
    )

    df.to_csv(LETTERS_CSV_FIX, index=False, encoding="utf-8")

    print("Saved fixed metadata to:", LETTERS_CSV_FIX)
    print(df[["letter_id", "sender", "recipient", "date_iso", "place_written"]].to_string())


if __name__ == "__main__":
    main()
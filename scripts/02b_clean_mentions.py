#!/usr/bin/env python

import sys
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd


INPUT = PROJECT_ROOT / "data/output/ner_entities.csv"
OUTPUT = PROJECT_ROOT / "data/output/ner_entities_cleaned.csv"


ALIASES = {
    # Persons
    "I. Andrić": "Ivo Andrić",
    "I. Andric": "Ivo Andrić",
    "Ivo Andric": "Ivo Andrić",
    "Ivo Andrić Maрсе": "Ivo Andrić",
    "Ivo Andrić Mарсеј": "Ivo Andrić",
    "Zdenka": "Zdenka Marković",
    "Tugomira Alaupovića": "Tugomir Alaupović",
    "Krleže": "Miroslav Krleža",
    "Andriji Ady": "Endre Ady",
    "Boy-Želenski": "Tadeusz Boy-Żeleński",
    "Bron. Grabowskoga": "Bronisław Grabowski",
    "Fr. Schützom": "Franz Schütz",
    "Nevistić": "Nevistić",
    "Dobronića": "Dobronić",

    # Places
    "Београд": "Beograd",
    "Београ": "Beograd",
    "Beogradu": "Beograd",
    "Zagrebu": "Zagreb",
    "Zagreba": "Zagreb",
    "Вишеград": "Višegrad",
    "Višegradu": "Višegrad",
    "Сарајево": "Sarajevo",
    "Атина": "Atina",
    "Atinu": "Atina",
    "Marseilla": "Marseille",
    "Maribora": "Maribor",
    "Frankfurta": "Frankfurt",
    "Weimara": "Weimar",
    "Fribourgu": "Fribourg",
    "Poljsku": "Poljska",
    "Provenci": "Provansa",
    "Avignona": "Avignon",
    "Nimes": "Nîmes",
    "Carigrada": "Carigrad",
    "Женева": "Ženeva",
    "Женеваенева": "Ženeva",
    "ŽeneGeva": "Ženeva",
    "Ženeva": "Ženeva",
    "Žene": "Ženeva",
    "енева": "Ženeva",
    "тина": "Atina",
    "Francusku": "Francuska",
    "Francuze": "Francuzi",
    "Alpe": "Alpi",
    
    "ArlesNimes": "Arles" + "Nimes",
    "Eisen Kappel Karnten": "Eisenkappel",

    # Organisations / publications / works
    "Tagblatta": "Agramer Tagblatt",
    "Hrvatske Revije": "Hrvatska revija",
    "Srp. Knjiž. Zadruzi": "Srpska književna zadruga",
    "Pripovetke": "Pripovetke",
    "Akademije": "Akademija",

    # Additional places / OCR variants
"тина": "Atina",
"Atinu": "Atina",
"Женева": "Ženeva",
"енева": "Ženeva",
"Žene": "Ženeva",
"Ženeva": "Ženeva",
"Mapcej": "Marseille",
"Maрсеј": "Marseille",
"Maрсе": "Marseille",
"Avignona": "Avignon",
"Nimes": "Nîmes",
"Provenci": "Provansa",
"Grenobl": "Grenoble",
"Francusku": "Francuska",

# Additional persons
"Zdenka": "Zdenka Marković",
"Tugomira Alaupovića": "Tugomir Alaupović",
"Andriji Ady": "Endre Ady",
"Bron. Grabowskoga": "Bronisław Grabowski",
"Fr. Schützom": "Franz Schütz",

# Additional organizations / publications
"Tagblatta": "Agramer Tagblatt",


}


DROP_EXACT = {
    "Ma",
    "At",
    "Ge",
    "Uskrsa",
    "Uskrs",
    "Varoš",
    "Bog",
    "Ma",
    "Mari",
    "At",
    "Bog",
    "Varoš",
    "Uskrs",
    "Uskrsa",
    "Francu",
    "Francuze",
    "Francusku",
}


DROP_CONTAINS = {
    "KarntenAustrijaБеоград",
    "I Yougoslavie",
}


def clean_surface(text: str) -> str:
    text = str(text)
    text = text.replace("##", "")
    text = text.replace(" - ", "-")
    text = " ".join(text.split())
    return text.strip(" ,.;:()[]{}\"'“”„")


def normalize_entity_label(text: str) -> str:
    text = clean_surface(text)
    return ALIASES.get(text, text)


def should_drop(text: str, label: str) -> bool:
    text = clean_surface(text)

    if text in DROP_EXACT:
        return True

    if any(part in text for part in DROP_CONTAINS):
        return True

    # Remove very short accidental entities such as "Ma", "At", "Ge".
    if label in {"PER", "LOC", "ORG"} and len(text) <= 2:
        return True

    # Remove WordPiece fragments that survived.
    if text.startswith("##"):
        return True

    return False


def merge_wordpieces(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge only true BERT WordPiece fragments.

    Important:
    DATE entities are never merged here, because regex-date output can overlap
    and otherwise produces bad strings such as 192719271927.
    """
    df = df.sort_values(["letter_id", "start", "end"]).reset_index(drop=True)

    merged = []
    current = None

    for _, row in df.iterrows():
        row = row.to_dict()
        raw_text = str(row["text"])
        label = str(row["label"])

        # Never merge dates.
        if label == "DATE":
            if current is not None:
                merged.append(current)
                current = None
            row["text"] = clean_surface(raw_text)
            merged.append(row)
            continue

        if current is None:
            row["_raw_text"] = raw_text
            row["text"] = clean_surface(raw_text)
            current = row
            continue

        same_letter = row["letter_id"] == current["letter_id"]
        same_label = row["label"] == current["label"]
        same_model = row.get("model") == current.get("model")
        is_wordpiece = raw_text.strip().startswith("##")
        touches = int(row["start"]) <= int(current["end"]) + 2

        if same_letter and same_label and same_model and is_wordpiece and touches:
            piece = raw_text.strip().replace("##", "")
            current["text"] = clean_surface(str(current["text"]) + piece)
            current["end"] = max(int(current["end"]), int(row["end"]))
            current["score"] = min(float(current["score"]), float(row["score"]))
        else:
            merged.append(current)
            row["_raw_text"] = raw_text
            row["text"] = clean_surface(raw_text)
            current = row

    if current is not None:
        merged.append(current)

    out = pd.DataFrame(merged)
    if "_raw_text" in out.columns:
        out = out.drop(columns=["_raw_text"])
    return out


def remove_contained_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    If both '1927' and '20 aprila 1927' exist at overlapping offsets,
    keep only the longer date.
    """
    keep = []

    for letter_id, group in df.groupby("letter_id"):
        rows = group.to_dict("records")

        for i, row in enumerate(rows):
            if row["label"] != "DATE":
                keep.append(row)
                continue

            start = int(row["start"])
            end = int(row["end"])
            text = str(row["text"])

            contained = False
            for j, other in enumerate(rows):
                if i == j or other["label"] != "DATE":
                    continue

                o_start = int(other["start"])
                o_end = int(other["end"])
                o_text = str(other["text"])

                if o_start <= start and end <= o_end and len(o_text) > len(text):
                    contained = True
                    break

            if not contained:
                keep.append(row)

    return pd.DataFrame(keep)

def split_merged_entities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split OCR/NER-merged entities that should be represented as
    separate entities in the knowledge graph.

    Examples:
        ArlesNimes / ArlesNîmes -> Arles + Nîmes
        Arles — Nimes -> Arles + Nîmes
    """
    new_rows = []

    for _, row in df.iterrows():
        row = row.to_dict()
        text = str(row["text"])

        if text in {"ArlesNimes", "ArlesNîmes"} and row["label"] == "LOC":
            start = int(row["start"])
            score = float(row["score"])

            row1 = row.copy()
            row1["text"] = "Arles"
            row1["start"] = start
            row1["end"] = start + len("Arles")
            row1["score"] = score

            row2 = row.copy()
            row2["text"] = "Nimes"
            row2["start"] = start + len("Arles")
            row2["end"] = int(row["end"])
            row2["score"] = score

            new_rows.extend([row1, row2])
        elif row["label"] == "LOC" and re.search(r"\s+[–—-]\s+", text):
            start = int(row["start"])
            score = float(row["score"])

            for match in re.finditer(r"[^–—-]+", text):
                part = clean_surface(match.group(0))
                if not part:
                    continue

                part_row = row.copy()
                part_row["text"] = normalize_entity_label(part)
                part_row["start"] = start + match.start() + (len(match.group(0)) - len(match.group(0).lstrip()))
                part_row["end"] = part_row["start"] + len(part)
                part_row["score"] = score
                new_rows.append(part_row)
        else:
            new_rows.append(row)

    return pd.DataFrame(new_rows)

def main():
    df = pd.read_csv(INPUT)

    df = merge_wordpieces(df)
    df = remove_contained_dates(df)

    df["text"] = df["text"].astype(str).map(clean_surface)
    df = df[~df.apply(lambda r: should_drop(r["text"], r["label"]), axis=1)].copy()

    df["text"] = df["text"].map(normalize_entity_label)

    df = split_merged_entities(df)

    df = df.drop_duplicates(
        subset=["letter_id", "text", "label", "start", "end", "model"]
    )

    df.to_csv(OUTPUT, index=False, encoding="utf-8")

    print(f"Saved cleaned mentions to {OUTPUT}")
    print(df["label"].value_counts())
    print(df.head(50).to_string())


if __name__ == "__main__":
    main()
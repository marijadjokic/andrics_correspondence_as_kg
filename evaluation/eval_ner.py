import argparse
import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path


TARGET_TYPES = {"PER", "LOC", "ORG", "MISC"}

def normalize_text(text: str) -> str:
    """
    Normalize entity text for matching:
    - trim spaces
    - transliterate Serbian Cyrillic to Latin
    - lowercase
    - remove diacritics: Andrić -> Andric, Ženeva -> Zeneva
    - normalize whitespace
    """
    if text is None:
        return ""

    text = str(text).strip()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def read_csv(path: str) -> list[dict]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    required_columns = {"letter_id", "text", "label"}
    missing = required_columns - set(reader.fieldnames or [])

    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")

    return rows


def build_counter(rows: list[dict]) -> Counter:
    """
    Build a counter using letter ID, entity text, and entity type.

    Start and end offsets are intentionally ignored because tokenizer-provided
    boundaries may not reliably match the manually annotated gold spans.
    """
    counter = Counter()

    for row in rows:
        label = str(row.get("label", "")).strip().upper()

        if label not in TARGET_TYPES:
            continue

        text = str(row.get("text", "")).strip()

        if not text:
            continue

        letter_id = str(row.get("letter_id", "")).strip()

        key = (letter_id, text, label)
        counter[key] += 1

    return counter


def compute_metrics(gold_counter: Counter, pred_counter: Counter) -> list[dict]:
    results = []

    for entity_type in ["PER", "LOC", "ORG", "MISC"]:
        gold_type = Counter({
            key: count for key, count in gold_counter.items()
            if key[2] == entity_type
        })

        pred_type = Counter({
            key: count for key, count in pred_counter.items()
            if key[2] == entity_type
        })

        gold_count = sum(gold_type.values())
        pred_count = sum(pred_type.values())

        correct = sum(
            min(gold_type[key], pred_type[key])
            for key in gold_type
        )

        precision = correct / pred_count if pred_count else 0.0
        recall = correct / gold_count if gold_count else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall > 0
            else 0.0
        )

        results.append({
            "Type": entity_type,
            "Gold": gold_count,
            "Predicted": pred_count,
            "Correct": correct,
            "Precision": precision,
            "Recall": recall,
            "F1": f1,
        })

    gold_total = sum(row["Gold"] for row in results)
    pred_total = sum(row["Predicted"] for row in results)
    correct_total = sum(row["Correct"] for row in results)

    micro_precision = correct_total / pred_total if pred_total else 0.0
    micro_recall = correct_total / gold_total if gold_total else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if micro_precision + micro_recall > 0
        else 0.0
    )

    results.append({
        "Type": "micro avg.",
        "Gold": gold_total,
        "Predicted": pred_total,
        "Correct": correct_total,
        "Precision": micro_precision,
        "Recall": micro_recall,
        "F1": micro_f1,
    })

    return results


def save_results(results: list[dict], out_path: str) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["Type", "Gold", "Predicted", "Correct", "Precision", "Recall", "F1"]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in results:
            writer.writerow({
                "Type": row["Type"],
                "Gold": row["Gold"],
                "Predicted": row["Predicted"],
                "Correct": row["Correct"],
                "Precision": f"{row['Precision']:.3f}",
                "Recall": f"{row['Recall']:.3f}",
                "F1": f"{row['F1']:.3f}",
            })


def save_errors(gold_counter: Counter, pred_counter: Counter, out_path: str) -> None:
    """
    Save false negatives and false positives for manual inspection.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    false_negatives = gold_counter - pred_counter
    false_positives = pred_counter - gold_counter

    fieldnames = ["error_type", "letter_id", "text", "label", "count"]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for (letter_id, text, label), count in false_negatives.items():
            writer.writerow({
                "error_type": "FN",
                "letter_id": letter_id,
                "text": text,
                "label": label,
                "count": count,
            })

        for (letter_id, text, label), count in false_positives.items():
            writer.writerow({
                "error_type": "FP",
                "letter_id": letter_id,
                "text": text,
                "label": label,
                "count": count,
            })


def print_results(results: list[dict]) -> None:
    header = f"{'Type':<12} {'Gold':>6} {'Predicted':>10} {'Correct':>8} {'Precision':>10} {'Recall':>8} {'F1':>8}"
    print(header)
    print("-" * len(header))

    for row in results:
        print(
            f"{row['Type']:<12} "
            f"{row['Gold']:>6} "
            f"{row['Predicted']:>10} "
            f"{row['Correct']:>8} "
            f"{row['Precision']:>10.3f} "
            f"{row['Recall']:>8.3f} "
            f"{row['F1']:>8.3f}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate NER by letter ID, entity text, and entity type."
    )

    parser.add_argument(
        "--gold",
        required=True,
        help="Path to the gold CSV file."
    )

    parser.add_argument(
        "--pred",
        required=True,
        help="Path to the model output CSV file."
    )

    parser.add_argument(
        "--out",
        default=None,
        help="Optional path to save evaluation results as CSV."
    )

    parser.add_argument(
        "--errors",
        default=None,
        help="Optional path to save false positives and false negatives as CSV."
    )

    args = parser.parse_args()

    gold_rows = read_csv(args.gold)
    pred_rows = read_csv(args.pred)

    gold_counter = build_counter(gold_rows)
    pred_counter = build_counter(pred_rows)

    results = compute_metrics(gold_counter, pred_counter)

    print_results(results)

    if args.out:
        save_results(results, args.out)
        print(f"\nSaved evaluation results to: {args.out}")

    if args.errors:
        save_errors(gold_counter, pred_counter, args.errors)
        print(f"Saved error analysis to: {args.errors}")


if __name__ == "__main__":
    main()
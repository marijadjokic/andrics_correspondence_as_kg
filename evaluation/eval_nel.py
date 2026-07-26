#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

import pandas as pd


def load_entities(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"label": str})
    df["label"] = df["label"].astype(str).str.strip()
    df["wikidata_uri"] = df.get("wikidata_uri", pd.Series([""] * len(df)))
    df["wikidata_uri"] = df["wikidata_uri"].fillna("")
    return df


def build_link_map(df: pd.DataFrame) -> Dict[tuple[str, str], str]:
    """Build a lookup of linked entities by normalized label and type."""
    linked = df[df["wikidata_uri"].astype(bool)]

    def key(row: pd.Series) -> tuple[str, str]:
        entity_type = row.get("type", "")
        return (
            str(row["label"]).strip().lower(),
            str(entity_type).strip().upper(),
        )

    return {key(row): row["wikidata_uri"] for _, row in linked.iterrows()}


def evaluate(gold_df: pd.DataFrame, sys_df: pd.DataFrame) -> Dict[str, float]:
    gold_map = build_link_map(gold_df)
    sys_map = build_link_map(sys_df)

    # Overall correct
    correct = sum(1 for k, uri in sys_map.items() if k in gold_map and gold_map[k] and gold_map[k] == uri)

    precision = correct / len(sys_map) if sys_map else 0.0
    recall = correct / len(gold_map) if gold_map else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    coverage = len(sys_df) / len(gold_df) if len(gold_df) else 0.0

    # Overall accuracy: correct / union of gold and system keys
    union_size = len(set(list(gold_map.keys()) + list(sys_map.keys())))
    accuracy = correct / union_size if union_size else 0.0

    # Per-type metrics for PER, LOC, ORG
    types = ["PER", "LOC", "ORG"]
    per_type = {}
    for typ in types:
        gold_k = {k: v for k, v in gold_map.items() if k[1] == typ}
        sys_k = {k: v for k, v in sys_map.items() if k[1] == typ}
        correct_t = sum(1 for k, uri in sys_k.items() if k in gold_k and gold_k[k] and gold_k[k] == uri)

        prec_t = correct_t / len(sys_k) if sys_k else 0.0
        rec_t = correct_t / len(gold_k) if gold_k else 0.0
        f1_t = 2 * prec_t * rec_t / (prec_t + rec_t) if (prec_t + rec_t) > 0 else 0.0

        union_size = len(set(gold_k.keys()) | set(sys_k.keys()))
        acc_t = correct_t / union_size if union_size else 0.0

        per_type[typ] = {
            "gold_linked": len(gold_k),
            "sys_linked": len(sys_k),
            "correct_links": correct_t,
            "precision": prec_t,
            "recall": rec_t,
            "f1": f1_t,
            "accuracy": acc_t,
        }

    return {
        "gold_linked": len(gold_map),
        "sys_linked": len(sys_map),
        "correct_links": correct,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "coverage": coverage,
        "per_type": per_type,
    }


def build_results_table(stats: Dict[str, float]) -> List[dict]:
    results = []

    for typ in ["PER", "LOC", "ORG"]:
        t = stats["per_type"].get(typ, {})
        results.append({
            "Type": typ,
            "Gold": t.get("gold_linked", 0),
            "Predicted": t.get("sys_linked", 0),
            "Correct": t.get("correct_links", 0),
            "Precision": t.get("precision", 0.0),
            "Recall": t.get("recall", 0.0),
            "F1": t.get("f1", 0.0),
            "Accuracy": t.get("accuracy", 0.0),
        })

    results.append({
        "Type": "micro avg.",
        "Gold": stats["gold_linked"],
        "Predicted": stats["sys_linked"],
        "Correct": stats["correct_links"],
        "Precision": stats["precision"],
        "Recall": stats["recall"],
        "F1": stats["f1"],
        "Accuracy": stats.get("accuracy", 0.0),
    })

    return results


def print_results(results: List[dict]) -> None:
    header = (
        f"{'Type':<12} {'Gold':>6} {'Predicted':>10} {'Correct':>8} "
        f"{'Precision':>10} {'Recall':>8} {'F1':>8} {'Accuracy':>9}"
    )
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
            f"{row['F1']:>8.3f} "
            f"{row['Accuracy']:>9.3f}"
        )


def save_results(results: List[dict], out_path: str) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["Type", "Gold", "Predicted", "Correct", "Precision", "Recall", "F1", "Accuracy"]

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
                "Accuracy": f"{row['Accuracy']:.3f}",
            })


def save_errors(gold_df: pd.DataFrame, sys_df: pd.DataFrame, out_path: str) -> None:
    """Save false negatives and false positives for manual inspection."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    gold_map = build_link_map(gold_df)
    sys_map = build_link_map(sys_df)

    fieldnames = ["error_type", "label", "type", "wikidata_uri"]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for (label, entity_type), wikidata_uri in gold_map.items():
            if sys_map.get((label, entity_type)) != wikidata_uri:
                writer.writerow({
                    "error_type": "FN",
                    "label": label,
                    "type": entity_type,
                    "wikidata_uri": wikidata_uri,
                })

        for (label, entity_type), wikidata_uri in sys_map.items():
            if gold_map.get((label, entity_type)) != wikidata_uri:
                writer.writerow({
                    "error_type": "FP",
                    "label": label,
                    "type": entity_type,
                    "wikidata_uri": wikidata_uri,
                })


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate NEL (entity linking) results against gold entities CSV")

    ap.add_argument("--gold", required=True, help="Path to the gold entities CSV file.")
    ap.add_argument("--pred", required=True, help="Path to the system entities CSV file.")
    ap.add_argument("--out", default=None, help="Optional path to save evaluation results as CSV.")
    ap.add_argument(
        "--errors",
        default=None,
        help="Optional path to save false positives and false negatives as CSV.",
    )

    args = ap.parse_args()

    gold_df = load_entities(Path(args.gold))
    sys_df = load_entities(Path(args.pred))

    stats = evaluate(gold_df, sys_df)
    results = build_results_table(stats)

    print_results(results)
    print(f"\nEntity coverage (system/gold): {stats['coverage']:.4f}")

    if args.out:
        save_results(results, args.out)
        print(f"\nSaved evaluation results to: {args.out}")

    if args.errors:
        save_errors(gold_df, sys_df, args.errors)
        print(f"Saved error analysis to: {args.errors}")


if __name__ == "__main__":
    main()

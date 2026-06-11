#!/usr/bin/env python
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import argparse
from pathlib import Path

from andric_kg.io import read_csv_records, write_csv_records
from andric_kg.linking import build_entities_table
from andric_kg.metadata import enrich_letters_with_metadata
from andric_kg.utils import load_config


def main() -> None:
    ap = argparse.ArgumentParser(description="Infer letter metadata and link entities.")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(cfg["output"]["dir"])
    letters_csv = out_dir / cfg["output"]["letters_csv"]
    mentions_csv = out_dir / cfg["output"]["mentions_csv"]
    entities_csv = out_dir / cfg["output"]["entities_csv"]

    letters = read_csv_records(letters_csv)
    mentions = read_csv_records(mentions_csv)
    enriched_letters = enrich_letters_with_metadata(letters, mentions, cfg)
    entities = build_entities_table(mentions, cfg)

    write_csv_records(letters_csv, enriched_letters)
    write_csv_records(entities_csv, entities)
    print(f"Updated {letters_csv}")
    print(f"Wrote {len(entities)} entities to {entities_csv}")


if __name__ == "__main__":
    main()

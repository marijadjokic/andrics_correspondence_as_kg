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
from andric_kg.ner import run_ner_for_letters
from andric_kg.utils import load_config


def main() -> None:
    ap = argparse.ArgumentParser(description="Run NER over segmented letters.")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--letters", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(cfg["output"]["dir"])
    letters_csv = Path(args.letters or out_dir / cfg["output"]["letters_csv"])
    mentions_csv = Path(args.out or out_dir / cfg["output"]["mentions_csv"])

    letters = read_csv_records(letters_csv)
    mentions = run_ner_for_letters(letters, cfg)
    write_csv_records(mentions_csv, mentions)
    print(f"Wrote {len(mentions)} mentions to {mentions_csv}")


if __name__ == "__main__":
    main()

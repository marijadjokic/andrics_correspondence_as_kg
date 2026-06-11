#!/usr/bin/env python
from __future__ import annotations
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
from pathlib import Path

from andric_kg.io import write_csv_records
from andric_kg.pagexml import parse_pagexml_dir
from andric_kg.segment import records_to_dicts, split_lines_into_letters
from andric_kg.utils import load_config


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert Transkribus PAGE XML to segmented letter records.")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--pagexml-dir", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    pagexml_dir = Path(args.pagexml_dir or cfg["transkribus"]["pagexml_dir"])
    output_dir = Path(cfg["output"]["dir"])
    out_csv = Path(args.out or output_dir / cfg["output"]["letters_csv"])

    lines = parse_pagexml_dir(pagexml_dir)
    if not lines:
        raise SystemExit(f"No PAGE XML lines found in {pagexml_dir}")

    records = split_lines_into_letters(lines) if cfg.get("extraction", {}).get("split_letters", True) else []
    if not records:
        from andric_kg.segment import LetterRecord
        text = "\n".join(l.text for l in lines)
        records = [LetterRecord("letter_0001", ";".join(sorted({l.page_file for l in lines})), "", "", text)]

    rows = records_to_dicts(records)
    write_csv_records(out_csv, rows)
    print(f"Wrote {len(rows)} letters to {out_csv}")


if __name__ == "__main__":
    main()

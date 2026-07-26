from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import csv


def read_csv_records(path: str | Path) -> List[Dict[str, Any]]:
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [{k: (v if v is not None else "") for k, v in row.items()} for row in reader]


def write_csv_records(path: str | Path, records: List[Dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write("")
        return
    fieldnames = list(records[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow({k: (v if v is not None else "") for k, v in row.items()})

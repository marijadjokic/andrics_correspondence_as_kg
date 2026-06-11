from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def read_csv_records(path: str | Path) -> List[Dict[str, Any]]:
    df = pd.read_csv(path).fillna("")
    return df.to_dict(orient="records")


def write_csv_records(path: str | Path, records: List[Dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(path, index=False, encoding="utf-8")

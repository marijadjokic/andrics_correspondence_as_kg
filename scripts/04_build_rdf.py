#!/usr/bin/env python
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import argparse
from pathlib import Path

from andric_kg.io import read_csv_records
from andric_kg.rdf_builder import build_rdf_graph, serialize_graph
from andric_kg.utils import load_config


def main() -> None:
    ap = argparse.ArgumentParser(description="Build RDF graph from extracted letters/entities/mentions.")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(cfg["output"]["dir"])
    letters = read_csv_records(out_dir / cfg["output"]["letters_fixed_csv"])
    ner_entities = read_csv_records(out_dir / cfg["output"]["ner_entities_csv"])
    entities = read_csv_records(out_dir / cfg["output"]["entities_csv"])

    g = build_rdf_graph(letters, entities, ner_entities, cfg)
    serialize_graph(g, out_dir, cfg["output"]["ttl"], cfg["output"]["jsonld"])
    print(f"Graph contains {len(g)} triples")
    print(f"Wrote {out_dir / cfg['output']['ttl']}")
    print(f"Wrote {out_dir / cfg['output']['jsonld']}")


if __name__ == "__main__":
    main()

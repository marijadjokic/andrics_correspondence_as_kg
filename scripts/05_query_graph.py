#!/usr/bin/env python
from __future__ import annotations

import argparse

from rdflib import Graph


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a SPARQL query over the generated RDF graph.")
    ap.add_argument("--ttl", required=True)
    ap.add_argument("--query", required=True)
    args = ap.parse_args()

    g = Graph()
    g.parse(args.ttl, format="turtle")
    query = open(args.query, "r", encoding="utf-8").read()
    rows = list(g.query(query))
    for row in rows:
        print("\t".join(str(x) for x in row))
    print(f"\n{len(rows)} result rows")


if __name__ == "__main__":
    main()

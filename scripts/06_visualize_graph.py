#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------
# Make sure the project package can be imported when the script is run
# from the project root or directly from the scripts/ folder.
# ---------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from andric_kg.io import read_csv_records
from andric_kg.utils import load_config
from andric_kg.visualize import (
    export_network_edges,
    plot_network,
    write_pyvis_html,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create CSV, PNG, and HTML visual network from letter-entity mentions."
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml file. Default: config.yaml",
    )

    parser.add_argument(
        "--png-label-font-size",
        type=int,
        default=18,
        help="Font size for node labels in the PNG network visualization. Default: 18",
    )

    parser.add_argument(
        "--html-label-font-size",
        type=int,
        default=28,
        help="Font size for node labels in the interactive HTML visualization. Default: 28",
    )

    parser.add_argument(
        "--node-size",
        type=int,
        default=1100,
        help="Node size for the PNG network visualization. Default: 1100",
    )

    parser.add_argument(
        "--figure-width",
        type=int,
        default=30,
        help="PNG canvas width in inches. Larger spreads nodes further apart. Default: 30",
    )

    parser.add_argument(
        "--figure-height",
        type=int,
        default=22,
        help="PNG canvas height in inches. Default: 22",
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=400,
        help="PNG output resolution (dots per inch). 300-400+ recommended for poster printing. Default: 400",
    )

    parser.add_argument(
        "--layout-k",
        type=float,
        default=1.4,
        help="Spring-layout node spacing; higher values reduce overlap in dense clusters. Default: 1.4",
    )

    parser.add_argument(
        "--layout-iterations",
        type=int,
        default=300,
        help="Spring-layout iteration count; higher settles into a cleaner layout. Default: 300",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for the layout, for reproducible node placement. Default: 42",
    )

    parser.add_argument(
        "--no-legend",
        action="store_true",
        help="Disable the entity-type color legend on the PNG visualization.",
    )

    parser.add_argument(
        "--legend-font-size",
        type=int,
        default=None,
        help="Font size for the legend labels, title, and swatches on the PNG visualization. "
        "Default: max(12, png-label-font-size - 4).",
    )

    args = parser.parse_args()

    cfg = load_config(args.config)

    out_dir = Path(cfg["output"]["dir"])

    mentions_path = out_dir / cfg["output"]["ner_entities_csv"]
    entities_path = out_dir / cfg["output"]["entities_csv"]

    edges_csv = out_dir / "entity_network_edges.csv"
    output_png = out_dir / "entity_network.png"
    output_html = out_dir / "entity_network.html"

    mentions = read_csv_records(mentions_path)
    entities = read_csv_records(entities_path)

    export_network_edges(
        mentions=mentions,
        entities=entities,
        output_csv=edges_csv,
    )

    plot_network(
        edges_csv=edges_csv,
        output_png=output_png,
        label_font_size=args.png_label_font_size,
        node_size=args.node_size,
        figure_width=args.figure_width,
        figure_height=args.figure_height,
        dpi=args.dpi,
        layout_k=args.layout_k,
        layout_iterations=args.layout_iterations,
        seed=args.seed,
        show_legend=not args.no_legend,
        legend_font_size=args.legend_font_size,
    )

    write_pyvis_html(
        edges_csv=edges_csv,
        output_html=output_html,
        label_font_size=args.html_label_font_size,
    )

    print(f"Wrote {edges_csv}")
    print(f"Wrote {output_png}")
    print(f"Wrote {output_html}")


if __name__ == "__main__":
    main()
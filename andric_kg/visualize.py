from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _read_edges(edges_csv: Path) -> List[dict]:
    with open(edges_csv, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def export_network_edges(
    mentions: List[dict],
    entities: List[dict],
    output_csv: Path,
) -> None:
    """
    Export a letter-entity network edge list.

    Output columns:
        source, target, source_type, target_type, weight

    Each edge connects:
        letter_id -> mentioned entity label
    """

    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    entity_type_by_label: Dict[str, str] = {}

    for ent in entities:
        label = _safe_str(ent.get("label"))
        ent_type = _safe_str(ent.get("type"))
        if label:
            entity_type_by_label[label] = ent_type or "ENTITY"

    edge_counter: Counter[Tuple[str, str, str, str]] = Counter()

    for mention in mentions:
        letter_id = _safe_str(mention.get("letter_id"))
        entity_label = _safe_str(mention.get("text"))
        entity_type = _safe_str(mention.get("label"))

        if not letter_id or not entity_label:
            continue

        # Prefer normalized entity type from entities.csv if available.
        entity_type = entity_type_by_label.get(entity_label, entity_type or "ENTITY")

        edge_counter[(letter_id, entity_label, "LETTER", entity_type)] += 1

    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["source", "target", "source_type", "target_type", "weight"],
        )
        writer.writeheader()

        for (source, target, source_type, target_type), weight in sorted(edge_counter.items()):
            writer.writerow(
                {
                    "source": source,
                    "target": target,
                    "source_type": source_type,
                    "target_type": target_type,
                    "weight": weight,
                }
            )


NODE_TYPE_LABELS = {
    "LETTER": "Letter",
    "PER": "Person",
    "LOC": "Place",
    "ORG": "Organization",
    "MISC": "Miscellaneous",
    "DATE": "Date",
    "ENTITY": "Other",
}


def plot_network(
    edges_csv: Path,
    output_png: Path,
    label_font_size: int = 18,
    node_size: int = 1100,
    figure_width: int = 30,
    figure_height: int = 22,
    dpi: int = 400,
    layout_k: float = 1.4,
    layout_iterations: int = 300,
    seed: int = 42,
    show_legend: bool = True,
) -> None:
    """
    Create a static PNG network visualization sized for large-format
    (poster) printing.

    Parameters
    ----------
    label_font_size:
        Controls the size of node labels in the PNG.
    node_size:
        Controls the base size of nodes in the PNG.
    figure_width, figure_height:
        Canvas size in inches. Larger canvases spread nodes further
        apart (in physical space) without shrinking labels, which is
        the main lever for reducing label overlap on a poster print.
    dpi:
        Output resolution. 300-400 is print-quality for large posters.
    layout_k:
        Optimal spring-layout node spacing. Higher values push nodes
        further apart, reducing overlap in dense clusters.
    layout_iterations:
        Number of spring-layout iterations; higher settles into a more
        untangled layout at the cost of longer runtime.
    show_legend:
        Whether to draw a legend mapping node color to entity type.
    """

    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    import networkx as nx

    edges_csv = Path(edges_csv)
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    rows = _read_edges(edges_csv)

    G = nx.Graph()

    for row in rows:
        source = _safe_str(row.get("source"))
        target = _safe_str(row.get("target"))
        source_type = _safe_str(row.get("source_type")) or "LETTER"
        target_type = _safe_str(row.get("target_type")) or "ENTITY"
        weight = int(float(row.get("weight", 1) or 1))

        if not source or not target:
            continue

        G.add_node(source, node_type=source_type)
        G.add_node(target, node_type=target_type)
        G.add_edge(source, target, weight=weight)

    if G.number_of_nodes() == 0:
        print("No nodes found. Empty network was not plotted.")
        return

    degree = dict(G.degree())

    # Larger nodes for more connected entities.
    node_sizes = [
        node_size + degree.get(node, 0) * 120
        for node in G.nodes()
    ]

    # Basic type-based colors for readability.
    color_by_type = {
        "LETTER": "#8fb8ec",
        "PER": "#ef9a9a",
        "LOC": "#a5d6a7",
        "ORG": "#f6c667",
        "MISC": "#c5b3e0",
        "DATE": "#cfcfcf",
        "ENTITY": "#bdbdbd",
    }

    node_colors = [
        color_by_type.get(G.nodes[node].get("node_type", "ENTITY"), "#dddddd")
        for node in G.nodes()
    ]

    fig, ax = plt.subplots(figsize=(figure_width, figure_height))

    pos = nx.spring_layout(
        G,
        k=layout_k,
        iterations=layout_iterations,
        seed=seed,
        weight="weight",
    )

    nx.draw_networkx_edges(
        G,
        pos,
        ax=ax,
        alpha=0.3,
        width=[
            max(0.6, min(3.0, G.edges[edge].get("weight", 1)))
            for edge in G.edges()
        ],
    )

    nx.draw_networkx_nodes(
        G,
        pos,
        ax=ax,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors="#555555",
        linewidths=0.7,
        alpha=0.95,
    )

    # White halo behind labels so text stays legible over edges/nodes.
    nx.draw_networkx_labels(
        G,
        pos,
        ax=ax,
        font_size=label_font_size,
        font_family="DejaVu Sans",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.5},
    )

    if show_legend:
        types_present = sorted(
            {G.nodes[node].get("node_type", "ENTITY") for node in G.nodes()},
            key=lambda t: list(color_by_type).index(t) if t in color_by_type else 99,
        )
        handles = [
            mpatches.Patch(
                facecolor=color_by_type.get(t, "#dddddd"),
                edgecolor="#555555",
                label=NODE_TYPE_LABELS.get(t, t),
            )
            for t in types_present
        ]
        ax.legend(
            handles=handles,
            loc="lower right",
            fontsize=max(12, label_font_size - 4),
            frameon=True,
            title="Entity type",
        )

    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def write_pyvis_html(
    edges_csv: Path,
    output_html: Path,
    label_font_size: int = 28,
) -> None:
    """
    Create an interactive HTML network visualization using PyVis.

    Parameters
    ----------
    label_font_size:
        Controls the size of node labels in the interactive HTML graph.
    """

    try:
        from pyvis.network import Network
    except ImportError as exc:
        raise ImportError(
            "PyVis is not installed. Install it with: pip install pyvis"
        ) from exc

    edges_csv = Path(edges_csv)
    output_html = Path(output_html)
    output_html.parent.mkdir(parents=True, exist_ok=True)

    rows = _read_edges(edges_csv)

    degree = defaultdict(int)

    for row in rows:
        source = _safe_str(row.get("source"))
        target = _safe_str(row.get("target"))

        if source and target:
            degree[source] += 1
            degree[target] += 1

    net = Network(
        height="900px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#222222",
        notebook=False,
        directed=False,
    )

    added_nodes = set()

    def add_node(node_id: str, node_type: str) -> None:
        if node_id in added_nodes:
            return

        added_nodes.add(node_id)

        size = 18 + min(degree.get(node_id, 1) * 3, 30)

        net.add_node(
            node_id,
            label=node_id,
            title=f"{node_id} ({node_type})",
            group=node_type,
            size=size,
            font={
                "size": label_font_size,
                "face": "arial",
                "color": "#222222",
            },
        )

    for row in rows:
        source = _safe_str(row.get("source"))
        target = _safe_str(row.get("target"))
        source_type = _safe_str(row.get("source_type")) or "LETTER"
        target_type = _safe_str(row.get("target_type")) or "ENTITY"
        weight = int(float(row.get("weight", 1) or 1))

        if not source or not target:
            continue

        add_node(source, source_type)
        add_node(target, target_type)

        net.add_edge(
            source,
            target,
            value=weight,
            title=f"mentions: {weight}",
        )

    net.set_options(
        f"""
        var options = {{
          "nodes": {{
            "font": {{
              "size": {label_font_size},
              "face": "arial",
              "color": "#222222"
            }},
            "borderWidth": 1,
            "shadow": false
          }},
          "edges": {{
            "smooth": false,
            "color": {{
              "opacity": 0.35
            }}
          }},
          "physics": {{
            "enabled": true,
            "barnesHut": {{
              "gravitationalConstant": -35000,
              "centralGravity": 0.25,
              "springLength": 180,
              "springConstant": 0.04,
              "damping": 0.09,
              "avoidOverlap": 0.2
            }},
            "stabilization": {{
              "enabled": true,
              "iterations": 1000
            }}
          }},
          "interaction": {{
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": true,
            "keyboard": true
          }}
        }}
        """
    )

    net.write_html(str(output_html), notebook=False)
"""Pyvis-based knowledge graph visualizer."""

from __future__ import annotations

from pathlib import Path

from pyvis.network import Network

from app.models.enums import KGEdgeType, KGNodeType
from app.schemas.knowledge_graph import KnowledgeGraphSnapshot

_NODE_COLORS = {
    KGNodeType.PAPER: "#4C78A8",
    KGNodeType.AUTHOR: "#F58518",
    KGNodeType.TOPIC: "#54A24B",
    KGNodeType.METHOD: "#B279A2",
    KGNodeType.DATASET: "#EECA3B",
    KGNodeType.CLAIM: "#72B7B2",
}

_EDGE_COLORS = {
    KGEdgeType.SUPPORTS: "#2CA02C",
    KGEdgeType.CONTRADICTS: "#D62728",
    KGEdgeType.REFERENCES: "#9467BD",
    KGEdgeType.USES: "#8C564B",
    KGEdgeType.BELONGS_TO: "#7F7F7F",
}


class KnowledgeGraphVisualizer:
    """Render interactive HTML knowledge graphs."""

    def render_html(
        self,
        snapshot: KnowledgeGraphSnapshot,
        *,
        output_path: Path,
        title: str = "SynaptiQ Knowledge Graph",
    ) -> str:
        """Export an interactive Pyvis HTML graph."""
        net = Network(
            height="720px",
            width="100%",
            bgcolor="#0f172a",
            font_color="#e2e8f0",
            directed=False,
            cdn_resources="remote",
        )
        net.barnes_hut(
            gravity=-12000,
            central_gravity=0.3,
            spring_length=120,
            spring_strength=0.05,
        )
        net.set_options(
            """
            {
              "physics": {"enabled": true, "stabilization": {"iterations": 120}},
              "interaction": {"hover": true, "navigationButtons": true}
            }
            """
        )

        for node in snapshot.nodes:
            size = 12 + int(node.importance * 18)
            color = _NODE_COLORS.get(node.node_type, "#94a3b8")
            if node.node_type == KGNodeType.CLAIM and node.properties.get("verdict") == "CONTRADICTED":
                color = "#ef4444"
            net.add_node(
                node.node_id,
                label=node.label[:48],
                title=f"{node.node_type.value}: {node.label}",
                color=color,
                size=size,
                group=node.node_type.value,
            )

        for edge in snapshot.edges:
            color = _EDGE_COLORS.get(edge.edge_type, "#cbd5e1")
            width = 1 + int(edge.weight * 4)
            if edge.edge_type == KGEdgeType.CONTRADICTS:
                width = max(width, 4)
            net.add_edge(
                edge.source_id,
                edge.target_id,
                title=edge.label or edge.edge_type.value,
                color=color,
                width=width,
                dashes=edge.edge_type == KGEdgeType.CONTRADICTS,
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        net.save_graph(str(output_path))
        html = output_path.read_text(encoding="utf-8").replace(
            "<title>pyvis</title>",
            f"<title>{title}</title>",
        )
        output_path.write_text(html, encoding="utf-8")
        return html

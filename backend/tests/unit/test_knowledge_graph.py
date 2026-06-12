"""Unit tests for knowledge graph builder and visualizer."""

from __future__ import annotations

from pathlib import Path

from app.models.enums import KGEdgeType, KGNodeType, Verdict
from app.services.kg.graph_builder import KnowledgeGraphBuilder
from app.services.kg.visualizer import KnowledgeGraphVisualizer


def test_graph_builder_creates_nodes_and_contradiction_edges() -> None:
    """Knowledge graph builder should materialize papers, claims, and contradictions."""
    builder = KnowledgeGraphBuilder()
    snapshot = builder.build(
        papers=[
            {
                "paper_id": "ss:1",
                "title": "Paper A",
                "authors": ["Alice"],
                "year": 2021,
                "relevance_score": 0.9,
            }
        ],
        verified_claims=[
            {
                "claim_id": "clm_a",
                "paper_id": "ss:1",
                "text": "Claim A",
                "topic": "insulin",
                "verdict": Verdict.SUPPORTED.value,
                "confidence": 0.9,
            },
            {
                "claim_id": "clm_b",
                "paper_id": "ss:1",
                "text": "Claim B",
                "topic": "insulin",
                "verdict": Verdict.SUPPORTED.value,
                "confidence": 0.8,
            },
        ],
        comparisons={"clusters": []},
        contradictions=[
            {
                "relation_id": "rel_1",
                "claim_a": "clm_a",
                "claim_b": "clm_b",
                "topic": "insulin",
                "rationale": "conflict",
                "confidence": 0.7,
            }
        ],
        research_gaps=[],
    )

    node_types = {node.node_type for node in snapshot.nodes}
    assert KGNodeType.PAPER in node_types
    assert KGNodeType.CLAIM in node_types
    assert KGNodeType.TOPIC in node_types
    assert any(edge.edge_type == KGEdgeType.CONTRADICTS for edge in snapshot.edges)
    assert snapshot.summary.contradictions_count >= 1


def test_visualizer_exports_html(tmp_path: Path) -> None:
    """Visualizer should write interactive HTML."""
    builder = KnowledgeGraphBuilder()
    snapshot = builder.build(
        papers=[{"paper_id": "ss:1", "title": "Paper A", "authors": [], "relevance_score": 0.5}],
        verified_claims=[],
        comparisons={"clusters": []},
        contradictions=[],
        research_gaps=[],
    )
    output_path = tmp_path / "graph.html"
    html = KnowledgeGraphVisualizer().render_html(snapshot, output_path=output_path)
    assert output_path.exists()
    assert "network" in html.lower()

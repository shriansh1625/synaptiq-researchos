"""Pydantic schemas for the knowledge graph system."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import KGEdgeType, KGNodeType


class KGNode(BaseModel):
    """Knowledge graph node."""

    node_id: str
    node_type: KGNodeType
    label: str
    properties: dict[str, object] = Field(default_factory=dict)
    cluster_id: str | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class KGEdge(BaseModel):
    """Knowledge graph edge."""

    edge_id: str
    source_id: str
    target_id: str
    edge_type: KGEdgeType
    label: str = ""
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict[str, object] = Field(default_factory=dict)


class KGCommunity(BaseModel):
    """Detected research community cluster."""

    community_id: str
    label: str
    member_node_ids: list[str] = Field(default_factory=list)
    topic: str = ""


class KGSummary(BaseModel):
    """High-level knowledge graph statistics."""

    nodes_count: int = 0
    edges_count: int = 0
    contradictions_count: int = 0
    top_topics: list[str] = Field(default_factory=list)
    communities_count: int = 0


class KnowledgeGraphSnapshot(BaseModel):
    """Complete knowledge graph artifact stored in ResearchState."""

    nodes: list[KGNode] = Field(default_factory=list)
    edges: list[KGEdge] = Field(default_factory=list)
    communities: list[KGCommunity] = Field(default_factory=list)
    summary: KGSummary = Field(default_factory=KGSummary)
    html_path: str | None = None
    html_content: str | None = None

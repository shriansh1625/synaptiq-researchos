"""Knowledge graph builder using NetworkX."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import networkx as nx

from app.models.enums import KGEdgeType, KGNodeType, RelationType, Verdict
from app.schemas.knowledge_graph import (
    KGCommunity,
    KGEdge,
    KGNode,
    KGSummary,
    KnowledgeGraphSnapshot,
)


class KnowledgeGraphBuilder:
    """Build a knowledge graph snapshot from ResearchState artifacts."""

    def build(
        self,
        *,
        papers: list[dict[str, Any]],
        verified_claims: list[dict[str, Any]],
        comparisons: dict[str, Any],
        contradictions: list[dict[str, Any]],
        research_gaps: list[dict[str, Any]],
    ) -> KnowledgeGraphSnapshot:
        nodes: dict[str, KGNode] = {}
        edges: list[KGEdge] = []
        edge_counter = 0

        topic_counts: Counter[str] = Counter()
        for paper in papers:
            paper_id = paper["paper_id"]
            nodes[paper_id] = KGNode(
                node_id=paper_id,
                node_type=KGNodeType.PAPER,
                label=paper.get("title", paper_id),
                properties={
                    "year": paper.get("year"),
                    "venue": paper.get("venue"),
                    "source": paper.get("source"),
                },
                importance=float(paper.get("relevance_score", 0.5)),
            )
            for author in paper.get("authors", [])[:5]:
                author_id = f"author:{author}"
                if author_id not in nodes:
                    nodes[author_id] = KGNode(
                        node_id=author_id,
                        node_type=KGNodeType.AUTHOR,
                        label=author,
                    )
                edge_counter += 1
                edges.append(
                    KGEdge(
                        edge_id=f"edge_{edge_counter}",
                        source_id=author_id,
                        target_id=paper_id,
                        edge_type=KGEdgeType.BELONGS_TO,
                        label="authored",
                    )
                )

        for claim in verified_claims:
            claim_id = claim["claim_id"]
            topic = claim.get("topic", "general")
            topic_id = f"topic:{topic}"
            topic_counts[topic] += 1
            if topic_id not in nodes:
                nodes[topic_id] = KGNode(
                    node_id=topic_id,
                    node_type=KGNodeType.TOPIC,
                    label=topic,
                    importance=0.6,
                )
            nodes[claim_id] = KGNode(
                node_id=claim_id,
                node_type=KGNodeType.CLAIM,
                label=claim.get("text", claim_id)[:80],
                properties={
                    "verdict": claim.get("verdict"),
                    "confidence": claim.get("confidence"),
                },
                importance=float(claim.get("confidence", 0.5)),
            )
            paper_id = claim.get("paper_id")
            if paper_id and paper_id in nodes:
                edge_counter += 1
                edge_type = (
                    KGEdgeType.SUPPORTS
                    if claim.get("verdict") == Verdict.SUPPORTED.value
                    else KGEdgeType.REFERENCES
                )
                edges.append(
                    KGEdge(
                        edge_id=f"edge_{edge_counter}",
                        source_id=claim_id,
                        target_id=paper_id,
                        edge_type=edge_type,
                        label=edge_type.value,
                        weight=float(claim.get("confidence", 0.5)),
                    )
                )
                edge_counter += 1
                edges.append(
                    KGEdge(
                        edge_id=f"edge_{edge_counter}",
                        source_id=claim_id,
                        target_id=topic_id,
                        edge_type=KGEdgeType.BELONGS_TO,
                        label="topic",
                    )
                )

        method_id = "method:systematic_review"
        nodes[method_id] = KGNode(
            node_id=method_id,
            node_type=KGNodeType.METHOD,
            label="Literature Review",
        )
        dataset_id = "dataset:corpus"
        nodes[dataset_id] = KGNode(
            node_id=dataset_id,
            node_type=KGNodeType.DATASET,
            label="Retrieved Corpus",
            properties={"paper_count": len(papers)},
        )
        for paper in papers:
            edge_counter += 1
            edges.append(
                KGEdge(
                    edge_id=f"edge_{edge_counter}",
                    source_id=method_id,
                    target_id=paper["paper_id"],
                    edge_type=KGEdgeType.USES,
                    label="analyzed",
                )
            )

        for cluster in comparisons.get("clusters", []):
            for relation in cluster.get("relations", []):
                claim_a = relation.get("claim_a")
                claim_b = relation.get("claim_b")
                if claim_a not in nodes or claim_b not in nodes:
                    continue
                edge_counter += 1
                relation_type = relation.get("relation_type", "")
                edge_type = (
                    KGEdgeType.CONTRADICTS
                    if relation_type == RelationType.CONTRADICTS.value
                    else KGEdgeType.SUPPORTS
                )
                edges.append(
                    KGEdge(
                        edge_id=f"edge_{edge_counter}",
                        source_id=claim_a,
                        target_id=claim_b,
                        edge_type=edge_type,
                        label=relation_type,
                        weight=float(relation.get("confidence", 0.5)),
                        properties={"rationale": relation.get("rationale", "")},
                    )
                )

        for contradiction in contradictions:
            claim_a = contradiction.get("claim_a")
            claim_b = contradiction.get("claim_b")
            if claim_a in nodes and claim_b in nodes:
                edge_counter += 1
                edges.append(
                    KGEdge(
                        edge_id=f"edge_{edge_counter}",
                        source_id=claim_a,
                        target_id=claim_b,
                        edge_type=KGEdgeType.CONTRADICTS,
                        label="contradiction",
                        weight=float(contradiction.get("confidence", 0.5)),
                    )
                )

        graph = nx.Graph()
        for node in nodes.values():
            graph.add_node(node.node_id)
        for edge in edges:
            graph.add_edge(edge.source_id, edge.target_id)

        communities = self._detect_communities(graph, nodes)
        for community in communities:
            for node_id in community.member_node_ids:
                if node_id in nodes:
                    nodes[node_id] = nodes[node_id].model_copy(
                        update={"cluster_id": community.community_id}
                    )

        summary = KGSummary(
            nodes_count=len(nodes),
            edges_count=len(edges),
            contradictions_count=sum(
                1 for edge in edges if edge.edge_type == KGEdgeType.CONTRADICTS
            ),
            top_topics=[topic for topic, _ in topic_counts.most_common(5)],
            communities_count=len(communities),
        )
        return KnowledgeGraphSnapshot(
            nodes=list(nodes.values()),
            edges=edges,
            communities=communities,
            summary=summary,
        )

    @staticmethod
    def _detect_communities(
        graph: nx.Graph,
        nodes: dict[str, KGNode],
    ) -> list[KGCommunity]:
        if graph.number_of_nodes() == 0:
            return []
        communities: list[KGCommunity] = []
        try:
            groups = list(nx.algorithms.community.greedy_modularity_communities(graph))
        except Exception:
            groups = [set(graph.nodes())]

        topic_members: dict[str, list[str]] = defaultdict(list)
        for node_id in graph.nodes():
            node = nodes.get(node_id)
            if node and node.node_type == KGNodeType.TOPIC:
                topic_members[node.label].append(node_id)

        for index, group in enumerate(groups):
            member_ids = sorted(group)
            label = f"Community {index + 1}"
            topic = ""
            for node_id in member_ids:
                node = nodes.get(node_id)
                if node and node.node_type == KGNodeType.TOPIC:
                    topic = node.label
                    label = f"{topic} cluster"
                    break
            communities.append(
                KGCommunity(
                    community_id=f"community_{index + 1}",
                    label=label,
                    member_node_ids=member_ids,
                    topic=topic,
                )
            )
        return communities

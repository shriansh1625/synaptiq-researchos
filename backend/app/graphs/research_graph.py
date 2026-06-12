"""LangGraph research pipeline with discovery through report generation."""

from __future__ import annotations

import uuid
from typing import Any, Awaitable, Callable

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.agents.brief_agent import BriefAgent
from app.agents.comparative_agent import ComparativeAgent
from app.agents.discovery_agent import DiscoveryAgent
from app.agents.gap_agent import GapAgent
from app.agents.verification_agent import VerificationAgent
from app.core.runtime_paths import get_graphs_dir
from app.graphs.checkpointer import get_checkpointer
from app.graphs.routing import route_after_discovery, route_after_verification
from app.graphs.state import ResearchState
from app.models.enums import AgentName
from app.schemas.knowledge_graph import KnowledgeGraphSnapshot
from app.services.agents.observability import persist_agent_log
from app.services.embeddings.embedding_pipeline import EmbeddingPipeline
from app.services.kg.graph_builder import KnowledgeGraphBuilder
from app.services.kg.visualizer import KnowledgeGraphVisualizer
from app.services.reports.report_service import ReportService

NodeFn = Callable[[ResearchState, RunnableConfig], Awaitable[dict[str, Any]]]


def _merge_errors(state: ResearchState, result: dict[str, Any]) -> list[dict[str, Any]]:
    return list(result.get("errors") or [])


async def _persist_log(
    state: ResearchState,
    config: RunnableConfig,
    result: dict[str, Any],
) -> None:
    session_id = state.get("session_id")
    db_session = (config.get("configurable") or {}).get("db_session")
    if session_id and db_session and result.get("agent_log"):
        await persist_agent_log(
            db_session,
            session_id=session_id,
            agent_result=result,
        )


async def node_discovery(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    """Run the discovery agent and merge outputs into state."""
    query = state.get("query") or state.get("question") or ""
    filters = state.get("filters") or {}
    control = state.get("control") or {}
    iteration = int(control.get("iteration", 0)) if isinstance(control, dict) else 0
    known_ids = {paper["paper_id"] for paper in state.get("papers", [])}

    pipeline = EmbeddingPipeline()
    agent = DiscoveryAgent(embedding_pipeline=pipeline)
    try:
        result = await agent.run(
            query=query,
            filters=filters,
            known_paper_ids=sorted(known_ids),
            iteration=iteration,
        )
    finally:
        await agent.close()

    if not result.get("papers"):
        from app.services.benchmark.curated_corpus import load_curated_papers
        from app.services.sources.paper_retrieval import PaperRetrievalService

        rescue = PaperRetrievalService()
        try:
            rescued, _meta = await rescue.search(
                query,
                limit=int(filters.get("max_papers", 8)),
                known_paper_ids=known_ids,
            )
            if rescued:
                result["papers"] = [paper.model_dump(mode="json") for paper in rescued]
                result.setdefault("errors", []).append(
                    {
                        "agent": AgentName.DISCOVERY.value,
                        "error_type": "DiscoveryRecovered",
                        "message": (
                            "Discovery agent failed; pipeline continued with "
                            "direct source retrieval fallback."
                        ),
                        "retryable": False,
                    }
                )
        finally:
            await rescue.close()

        if not result.get("papers"):
            curated = load_curated_papers(query)
            if curated:
                result["papers"] = [paper.model_dump(mode="json") for paper in curated]
                result.setdefault("errors", []).append(
                    {
                        "agent": AgentName.DISCOVERY.value,
                        "error_type": "CuratedCorpusFallback",
                        "message": (
                            "External APIs unavailable; continued with curated "
                            "research corpus for resilient analysis."
                        ),
                        "retryable": False,
                    }
                )
                next_control = dict(result.get("control") or control)
                next_control["sufficiency"] = "sufficient"
                result["control"] = next_control

    next_control = dict(result.get("control") or control)
    if next_control.get("sufficiency") == "insufficient":
        next_control["iteration"] = iteration + 1

    merged = {
        "query": query,
        "papers": result.get("papers", []),
        "retrieved_chunks": result.get("retrieved_chunks", []),
        "citations": result.get("citations", []),
        "confidence_scores": result.get("confidence_scores", {}),
        "chunks_indexed": result.get("chunks_indexed", []),
        "plan": result.get("plan", {}),
        "control": next_control,
        "messages": result.get("messages", []),
        "errors": _merge_errors(state, result),
    }
    if not merged["papers"]:
        merged["errors"].append(
            {
                "agent": AgentName.DISCOVERY.value,
                "error_type": "NoPapersFound",
                "message": (
                    "No papers were retrieved from external sources. "
                    "Semantic Scholar may be rate-limited; arXiv fallback was attempted."
                ),
                "retryable": True,
            }
        )
    await _persist_log(state, config, result)
    return merged


async def node_verification(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    """Run the verification agent."""
    query = state.get("query") or state.get("question") or ""
    options = state.get("options") or {}
    max_claims = int(options.get("max_claims_per_paper", 3))
    agent = VerificationAgent(max_claims_per_paper=max_claims)
    result = await agent.run(
        query=query,
        papers=state.get("papers", []),
        retrieved_chunks=state.get("retrieved_chunks", []),
    )

    control = dict(state.get("control") or {})
    control.update(result.get("control") or {})

    merged = {
        "verified_claims": result.get("verified_claims", []),
        "citations": result.get("citations", []),
        "confidence_scores": result.get("confidence_scores", {}),
        "control": control,
        "messages": result.get("messages", []),
        "errors": _merge_errors(state, result),
    }
    await _persist_log(state, config, result)
    return merged


async def node_comparative(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    """Run the comparative analysis agent."""
    query = state.get("query") or state.get("question") or ""
    agent = ComparativeAgent()
    result = await agent.run(
        query=query,
        verified_claims=state.get("verified_claims", []),
    )
    merged = {
        "comparisons": result.get("comparisons", {}),
        "contradictions": result.get("contradictions", []),
        "messages": result.get("messages", []),
        "errors": _merge_errors(state, result),
    }
    await _persist_log(state, config, result)
    return merged


async def node_gap(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    """Run the research gap detection agent."""
    query = state.get("query") or state.get("question") or ""
    agent = GapAgent()
    result = await agent.run(
        query=query,
        verified_claims=state.get("verified_claims", []),
        papers=state.get("papers", []),
        comparisons=state.get("comparisons", {}),
    )
    merged = {
        "research_gaps": result.get("research_gaps", []),
        "messages": result.get("messages", []),
        "errors": _merge_errors(state, result),
    }
    await _persist_log(state, config, result)
    return merged


async def node_brief(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    """Run the executive brief agent."""
    query = state.get("query") or state.get("question") or ""
    agent = BriefAgent()
    result = await agent.run(
        query=query,
        verified_claims=state.get("verified_claims", []),
        comparisons=state.get("comparisons", {}),
        research_gaps=state.get("research_gaps", []),
        contradictions=state.get("contradictions", []),
        papers=state.get("papers", []),
        citations=state.get("citations", []),
        kg_summary=state.get("knowledge_graph", {}).get("summary", {}),
    )
    brief = result.get("executive_brief", {})
    explainability = {
        "citations": brief.get("citations", []),
        "confidence_scores": result.get("confidence_scores", {}),
        "citation_integrity": brief.get("citation_integrity", {}),
        "contradiction_count": len(state.get("contradictions", [])),
        "supporting_papers": [paper.get("paper_id") for paper in state.get("papers", [])],
    }
    merged = {
        "executive_brief": brief,
        "confidence_scores": result.get("confidence_scores", {}),
        "explainability": explainability,
        "messages": result.get("messages", []),
        "errors": _merge_errors(state, result),
    }
    await _persist_log(state, config, result)
    return merged


async def node_knowledge_graph(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    """Build and visualize the knowledge graph."""
    builder = KnowledgeGraphBuilder()
    snapshot = builder.build(
        papers=state.get("papers", []),
        verified_claims=state.get("verified_claims", []),
        comparisons=state.get("comparisons", {}),
        contradictions=state.get("contradictions", []),
        research_gaps=state.get("research_gaps", []),
    )
    session_id = state.get("session_id") or uuid.uuid4().hex
    html_path = get_graphs_dir() / f"{session_id}.html"
    visualizer = KnowledgeGraphVisualizer()
    html_content = visualizer.render_html(
        snapshot,
        output_path=html_path,
        title=f"SynaptiQ Knowledge Graph — {state.get('query', '')[:80]}",
    )
    kg_payload = snapshot.model_dump(mode="json")
    kg_payload["html_path"] = str(html_path)
    kg_payload["html_content"] = html_content
    agent_log = {
        "agent_name": AgentName.KNOWLEDGE_GRAPH.value,
        "input_data": {
            "paper_count": len(state.get("papers", [])),
            "claim_count": len(state.get("verified_claims", [])),
        },
        "output_data": snapshot.summary.model_dump(mode="json"),
        "confidence_score": 1.0,
        "status": "success",
    }
    await _persist_log(state, config, {"agent_log": agent_log})
    return {
        "knowledge_graph": kg_payload,
        "messages": [
            {
                "agent": AgentName.KNOWLEDGE_GRAPH.value,
                "status": "success",
                "message": "Knowledge graph generated",
                "progress": 1.0,
            }
        ],
    }


async def node_pdf_report(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    """Generate and persist the executive PDF report."""
    query = state.get("query") or state.get("question") or ""
    brief = state.get("executive_brief") or {}
    knowledge_graph = state.get("knowledge_graph") or {}
    session_id = state.get("session_id")
    db_session = (config.get("configurable") or {}).get("db_session")
    report_id: str | None = None

    if session_id and db_session and brief:
        report_service = ReportService(db_session)
        created_id, _pdf_path = await report_service.create_report(
            session_id=uuid.UUID(str(session_id)),
            query=query,
            brief_payload=brief,
            papers=state.get("papers", []),
            knowledge_graph=knowledge_graph,
        )
        report_id = str(created_id)

    overall_confidence = brief.get("overall_confidence", 0.0)
    agent_log = {
        "agent_name": AgentName.REPORT.value,
        "input_data": {"query": query, "session_id": session_id},
        "output_data": {"report_id": report_id},
        "confidence_score": overall_confidence,
        "status": "success" if report_id else "skipped",
    }
    await _persist_log(state, config, {"agent_log": agent_log})
    return {
        "report_id": report_id or "",
        "messages": [
            {
                "agent": AgentName.REPORT.value,
                "status": "success" if report_id else "skipped",
                "message": "PDF report generated" if report_id else "PDF report skipped",
                "progress": 1.0,
            }
        ],
    }


def build_research_graph(
    *,
    discovery_node: NodeFn | None = None,
    verification_node: NodeFn | None = None,
    comparative_node: NodeFn | None = None,
    gap_node: NodeFn | None = None,
    brief_node: NodeFn | None = None,
    knowledge_graph_node: NodeFn | None = None,
    pdf_report_node: NodeFn | None = None,
):
    """Build the Sprint 5 end-to-end research graph."""
    graph = StateGraph(ResearchState)
    graph.add_node("discovery", discovery_node or node_discovery)
    graph.add_node("verification", verification_node or node_verification)
    graph.add_node("comparative", comparative_node or node_comparative)
    graph.add_node("gap", gap_node or node_gap)
    graph.add_node("brief", brief_node or node_brief)
    graph.add_node("knowledge_graph", knowledge_graph_node or node_knowledge_graph)
    graph.add_node("pdf_report", pdf_report_node or node_pdf_report)

    graph.add_edge(START, "discovery")
    graph.add_conditional_edges(
        "discovery",
        route_after_discovery,
        {
            "discovery": "discovery",
            "verification": "verification",
            END: END,
        },
    )
    graph.add_conditional_edges(
        "verification",
        route_after_verification,
        {
            "discovery": "discovery",
            "comparative": "comparative",
        },
    )
    graph.add_edge("comparative", "gap")
    graph.add_edge("gap", "brief")
    graph.add_edge("brief", "knowledge_graph")
    graph.add_edge("knowledge_graph", "pdf_report")
    graph.add_edge("pdf_report", END)

    return graph.compile(checkpointer=get_checkpointer())

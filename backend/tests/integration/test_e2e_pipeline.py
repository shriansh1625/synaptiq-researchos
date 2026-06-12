"""End-to-end pipeline test for Sprint 5 graph."""

from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableConfig

from app.agents.brief_agent import BriefAgent
from app.agents.comparative_agent import ComparativeAgent
from app.agents.discovery_agent import DiscoveryAgent
from app.agents.gap_agent import GapAgent
from app.agents.verification_agent import VerificationAgent
from app.graphs.research_graph import build_research_graph, node_knowledge_graph
from app.graphs.state import ResearchState
from app.models.enums import DiscoveryStatus, PaperSource, Sufficiency
from app.schemas.agent_io import DiscoveryOutput, DiscoveryPaperOutput
from app.services.embeddings.embedding_pipeline import EmbeddingPipeline
from app.services.retrieval.retrieval_pipeline import RetrievalPipeline
from app.services.sources.base_source import SourceSearchResult
from app.services.sources.paper_retrieval import PaperRetrievalService
from app.vector_store.faiss_store import FaissVectorStore
from tests.fixtures.fake_embedder import FakeEmbedder
from tests.fixtures.fake_gemini import FakeGeminiClient
from tests.fixtures.sample_papers import SAMPLE_PAPERS


def _discovery_output() -> DiscoveryOutput:
    return DiscoveryOutput(
        status=DiscoveryStatus.OK,
        query_plan=["fasting insulin"],
        papers=[
            DiscoveryPaperOutput(
                paper_id=paper.paper_id,
                title=paper.title,
                authors=paper.authors,
                year=paper.year,
                venue=paper.venue,
                doi=paper.doi,
                abstract=paper.abstract,
                citation_count=paper.citation_count,
                source=paper.source,
                url=paper.url,
                relevance_score=0.9,
                relevance_reason="Relevant",
            )
            for paper in SAMPLE_PAPERS[:2]
        ],
        sources_used=[PaperSource.SEMANTIC_SCHOLAR],
        sufficiency=Sufficiency.SUFFICIENT,
        discovery_confidence=0.85,
    )


class FakeSource:
    source = PaperSource.SEMANTIC_SCHOLAR

    async def safe_search(self, query: str, *, limit: int = 20) -> SourceSearchResult:
        return SourceSearchResult(papers=SAMPLE_PAPERS[:2], source=self.source)


@pytest.mark.asyncio
async def test_e2e_graph_runs_through_brief_and_knowledge_graph(tmp_path, monkeypatch) -> None:
    """End-to-end graph should reach brief and knowledge graph stages."""
    monkeypatch.setattr(
        "app.graphs.research_graph.get_graphs_dir",
        lambda: tmp_path / "graphs",
    )
    embedder = FakeEmbedder()
    vector_store = FaissVectorStore(index_dir=tmp_path / "faiss", dimension=embedder.dimension)
    embedding_pipeline = EmbeddingPipeline(embedder=embedder, vector_store=vector_store)
    retrieval_pipeline = RetrievalPipeline(embedder=embedder, vector_store=vector_store)
    llm = FakeGeminiClient(response=_discovery_output())

    async def fake_discovery(state: ResearchState, config: RunnableConfig) -> dict:
        agent = DiscoveryAgent(
            retrieval_service=PaperRetrievalService(sources=[FakeSource()]),
            llm_client=llm,
            embedding_pipeline=embedding_pipeline,
            retrieval_pipeline=retrieval_pipeline,
        )
        try:
            result = await agent.run(query=state.get("query", ""), filters=state.get("filters") or {})
        finally:
            await agent.close()
        return {
            "query": state.get("query", ""),
            "papers": result.get("papers", []),
            "retrieved_chunks": result.get("retrieved_chunks", []),
            "citations": result.get("citations", []),
            "confidence_scores": result.get("confidence_scores", {}),
            "control": result.get("control", {}),
            "messages": result.get("messages", []),
            "errors": result.get("errors", []),
        }

    async def fake_verification(state: ResearchState, config: RunnableConfig) -> dict:
        agent = VerificationAgent(llm_client=llm)
        result = await agent.run(
            query=state.get("query", ""),
            papers=state.get("papers", []),
            retrieved_chunks=state.get("retrieved_chunks", []),
        )
        return {
            "verified_claims": result.get("verified_claims", []),
            "citations": result.get("citations", []),
            "confidence_scores": result.get("confidence_scores", {}),
            "control": dict(state.get("control") or {}, unsupported_ratio=0.1, iteration=2, max_iterations=2),
            "messages": result.get("messages", []),
            "errors": result.get("errors", []),
        }

    async def fake_comparative(state: ResearchState, config: RunnableConfig) -> dict:
        agent = ComparativeAgent(llm_client=llm)
        result = await agent.run(query=state.get("query", ""), verified_claims=state.get("verified_claims", []))
        return {
            "comparisons": result.get("comparisons", {}),
            "contradictions": result.get("contradictions", []),
            "messages": result.get("messages", []),
            "errors": result.get("errors", []),
        }

    async def fake_gap(state: ResearchState, config: RunnableConfig) -> dict:
        agent = GapAgent(llm_client=llm)
        result = await agent.run(
            query=state.get("query", ""),
            verified_claims=state.get("verified_claims", []),
            papers=state.get("papers", []),
            comparisons=state.get("comparisons", {}),
        )
        return {"research_gaps": result.get("research_gaps", []), "messages": result.get("messages", []), "errors": []}

    async def fake_brief(state: ResearchState, config: RunnableConfig) -> dict:
        agent = BriefAgent(llm_client=llm)
        result = await agent.run(
            query=state.get("query", ""),
            verified_claims=state.get("verified_claims", []),
            comparisons=state.get("comparisons", {}),
            research_gaps=state.get("research_gaps", []),
            contradictions=state.get("contradictions", []),
            papers=state.get("papers", []),
            citations=state.get("citations", []),
        )
        return {
            "executive_brief": result.get("executive_brief", {}),
            "explainability": {"citations": result.get("executive_brief", {}).get("citations", [])},
            "messages": result.get("messages", []),
            "errors": result.get("errors", []),
        }

    async def stub_pdf(state: ResearchState, config: RunnableConfig) -> dict:
        return {"report_id": ""}

    graph = build_research_graph(
        discovery_node=fake_discovery,
        verification_node=fake_verification,
        comparative_node=fake_comparative,
        gap_node=fake_gap,
        brief_node=fake_brief,
        knowledge_graph_node=node_knowledge_graph,
        pdf_report_node=stub_pdf,
    )
    final_state = await graph.ainvoke(
        {
            "session_id": "e2e-session",
            "query": "Does intermittent fasting improve insulin sensitivity?",
            "filters": {"max_papers": 5},
            "papers": [],
            "retrieved_chunks": [],
            "citations": [],
            "confidence_scores": {},
            "verified_claims": [],
            "research_gaps": [],
            "contradictions": [],
            "errors": [],
            "messages": [],
        },
        config={"configurable": {"thread_id": "e2e-thread"}},
    )

    assert final_state["executive_brief"]
    assert final_state["knowledge_graph"]["summary"]["nodes_count"] > 0
    assert final_state["explainability"]

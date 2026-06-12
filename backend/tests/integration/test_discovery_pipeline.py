"""Integration tests for discovery graph pipeline."""

from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableConfig

from app.graphs.research_graph import build_research_graph
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
        query_plan=["intermittent fasting insulin"],
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
        discovery_confidence=0.7,
    )


class FakeSource:
    source = PaperSource.SEMANTIC_SCHOLAR

    async def safe_search(self, query: str, *, limit: int = 20) -> SourceSearchResult:
        return SourceSearchResult(papers=SAMPLE_PAPERS[:2], source=self.source)


@pytest.mark.asyncio
async def test_research_graph_discovery_node(tmp_path) -> None:
    """Research graph should execute discovery and populate state."""
    embedder = FakeEmbedder()
    vector_store = FaissVectorStore(index_dir=tmp_path, dimension=embedder.dimension)

    async def fake_node_discovery(state: ResearchState, config: RunnableConfig) -> dict:
        from app.agents.discovery_agent import DiscoveryAgent

        agent = DiscoveryAgent(
            retrieval_service=PaperRetrievalService(sources=[FakeSource()]),
            llm_client=FakeGeminiClient(response=_discovery_output()),
            embedding_pipeline=EmbeddingPipeline(embedder=embedder, vector_store=vector_store),
            retrieval_pipeline=RetrievalPipeline(embedder=embedder, vector_store=vector_store),
        )
        try:
            result = await agent.run(
                query=state.get("query", ""),
                filters=state.get("filters") or {},
            )
        finally:
            await agent.close()

        return {
            "query": state.get("query", ""),
            "papers": result.get("papers", []),
            "retrieved_chunks": result.get("retrieved_chunks", []),
            "citations": result.get("citations", []),
            "confidence_scores": result.get("confidence_scores", {}),
            "chunks_indexed": result.get("chunks_indexed", []),
            "plan": result.get("plan", {}),
            "control": result.get("control", {}),
            "messages": result.get("messages", []),
            "errors": result.get("errors", []),
        }

    async def stub_verification(state: ResearchState, config: RunnableConfig) -> dict:
        control = dict(state.get("control") or {})
        control.update({"iteration": 2, "max_iterations": 2, "unsupported_ratio": 0.0})
        return {
            "verified_claims": [{"claim_id": "c1"}, {"claim_id": "c2"}],
            "control": control,
        }

    async def stub_comparative(state: ResearchState, config: RunnableConfig) -> dict:
        return {"comparisons": {"clusters": []}}

    async def stub_gap(state: ResearchState, config: RunnableConfig) -> dict:
        return {"research_gaps": []}

    async def stub_brief(state: ResearchState, config: RunnableConfig) -> dict:
        return {"executive_brief": {"overall_confidence": 0.5}, "explainability": {}}

    async def stub_kg(state: ResearchState, config: RunnableConfig) -> dict:
        return {"knowledge_graph": {"summary": {"nodes_count": 0}, "nodes": [], "edges": []}}

    async def stub_pdf(state: ResearchState, config: RunnableConfig) -> dict:
        return {"report_id": ""}

    graph = build_research_graph(
        discovery_node=fake_node_discovery,
        verification_node=stub_verification,
        comparative_node=stub_comparative,
        gap_node=stub_gap,
        brief_node=stub_brief,
        knowledge_graph_node=stub_kg,
        pdf_report_node=stub_pdf,
    )
    config = {"configurable": {"thread_id": "test-thread"}}
    final_state = await graph.ainvoke(
        {
            "query": "Does intermittent fasting improve insulin sensitivity?",
            "filters": {"max_papers": 5},
            "papers": [],
            "retrieved_chunks": [],
            "citations": [],
            "confidence_scores": {},
            "errors": [],
            "messages": [],
        },
        config=config,
    )

    assert final_state["papers"]
    assert final_state["retrieved_chunks"]
    assert final_state["confidence_scores"]

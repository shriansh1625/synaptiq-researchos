"""Tests for discovery agent."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.discovery_agent import DiscoveryAgent
from app.models.enums import PaperSource
from app.services.embeddings.embedding_pipeline import EmbeddingPipeline
from app.services.retrieval.retrieval_pipeline import RetrievalPipeline
from app.services.sources.base_source import SourceSearchResult
from app.services.sources.paper_retrieval import PaperRetrievalService
from app.vector_store.faiss_store import FaissVectorStore
from tests.fixtures.fake_embedder import FakeEmbedder
from app.models.enums import DiscoveryStatus, Sufficiency
from app.schemas.agent_io import DiscoveryOutput, DiscoveryPaperOutput
from tests.fixtures.fake_gemini import FakeGeminiClient
from tests.fixtures.sample_papers import SAMPLE_PAPERS


def _discovery_output_from_candidates() -> DiscoveryOutput:
    papers = [
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
            relevance_reason="Directly relevant to the query.",
        )
        for paper in SAMPLE_PAPERS[:2]
    ]
    return DiscoveryOutput(
        status=DiscoveryStatus.OK,
        query_plan=["intermittent fasting insulin sensitivity"],
        papers=papers,
        sources_used=[PaperSource.SEMANTIC_SCHOLAR],
        sufficiency=Sufficiency.INSUFFICIENT,
        discovery_confidence=0.75,
    )


class FakeSource:
    source = PaperSource.SEMANTIC_SCHOLAR

    async def safe_search(self, query: str, *, limit: int = 20) -> SourceSearchResult:
        return SourceSearchResult(papers=SAMPLE_PAPERS[:2], source=self.source)


@pytest.mark.asyncio
async def test_discovery_agent_returns_structured_state(tmp_path) -> None:
    """Discovery agent should return papers, chunks, and confidence scores."""
    embedder = FakeEmbedder()
    vector_store = FaissVectorStore(index_dir=tmp_path, dimension=embedder.dimension)
    embedding_pipeline = EmbeddingPipeline(
        embedder=embedder,
        vector_store=vector_store,
    )
    retrieval_pipeline = RetrievalPipeline(
        embedder=embedder,
        vector_store=vector_store,
    )
    agent = DiscoveryAgent(
        retrieval_service=PaperRetrievalService(sources=[FakeSource()]),
        llm_client=FakeGeminiClient(response=_discovery_output_from_candidates()),
        embedding_pipeline=embedding_pipeline,
        retrieval_pipeline=retrieval_pipeline,
    )

    result = await agent.run(
        query="Does intermittent fasting improve insulin sensitivity?",
        filters={"max_papers": 5},
    )

    assert result["papers"]
    assert result["retrieved_chunks"]
    assert result["citations"]
    assert "confidence_scores" in result
    assert result["agent_log"]["status"] in {"success", "ok"}
    await agent.close()


@pytest.mark.asyncio
async def test_discovery_agent_filters_fabricated_papers(tmp_path) -> None:
    """Discovery agent should drop fabricated paper IDs and use retrieval fallback."""
    from app.models.enums import DiscoveryStatus, Sufficiency
    from app.schemas.agent_io import DiscoveryOutput, DiscoveryPaperOutput

    bad_output = DiscoveryOutput(
        status=DiscoveryStatus.OK,
        papers=[
            DiscoveryPaperOutput(
                paper_id="fabricated:999",
                title="Fake",
                authors=[],
                year=2024,
                venue=None,
                doi=None,
                abstract="fake",
                citation_count=0,
                source=PaperSource.SEMANTIC_SCHOLAR,
                url=None,
                relevance_score=0.9,
            )
        ],
        sufficiency=Sufficiency.INSUFFICIENT,
        discovery_confidence=0.1,
    )
    embedder = FakeEmbedder()
    vector_store = FaissVectorStore(index_dir=tmp_path, dimension=embedder.dimension)
    agent = DiscoveryAgent(
        retrieval_service=PaperRetrievalService(sources=[FakeSource()]),
        llm_client=FakeGeminiClient(response=bad_output),
        embedding_pipeline=EmbeddingPipeline(embedder=embedder, vector_store=vector_store),
        retrieval_pipeline=RetrievalPipeline(embedder=embedder, vector_store=vector_store),
        max_attempts=1,
    )

    result = await agent.run(query="test query")
    papers = result.get("papers") or []
    assert papers
    assert all(paper["paper_id"] != "fabricated:999" for paper in papers)
    await agent.close()

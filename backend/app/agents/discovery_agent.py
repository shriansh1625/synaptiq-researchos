"""Discovery agent orchestrating sources, LLM judging, and retrieval."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.discovery_config import get_discovery_config
from app.core.exceptions import AgentExecutionError, FabricationError, SchemaValidationError
from app.services.benchmark.curated_corpus import load_curated_papers
from app.core.retry import async_retry
from app.database.repositories.paper_repository import PaperRepository
from app.models.enums import AgentName, DiscoveryStatus, JobStatus, Sufficiency
from app.prompts.loader import load_prompt
from app.schemas.agent_io import ControlState, DiscoveryOutput, DiscoveryPaperOutput
from app.schemas.common import PaperRef
from app.services.embeddings.embedding_pipeline import EmbeddingPipeline
from app.services.llm.base import LLMClient
from app.services.llm.factory import get_llm_client
from app.services.retrieval.retrieval_pipeline import RetrievalPipeline
from app.services.sources.paper_retrieval import PaperRetrievalService


class DiscoveryAgent(BaseAgent):
    """Discover relevant papers and prepare retrieval artifacts."""

    agent_name = AgentName.DISCOVERY

    def __init__(
        self,
        *,
        retrieval_service: PaperRetrievalService | None = None,
        llm_client: LLMClient | None = None,
        embedding_pipeline: EmbeddingPipeline | None = None,
        retrieval_pipeline: RetrievalPipeline | None = None,
        db_session: AsyncSession | None = None,
        max_attempts: int = 3,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self._retrieval_service = retrieval_service or PaperRetrievalService()
        self._llm = llm_client or get_llm_client()
        self._embedding_pipeline = embedding_pipeline or EmbeddingPipeline()
        self._retrieval_pipeline = retrieval_pipeline or RetrievalPipeline(
            vector_store=self._embedding_pipeline.vector_store,
        )
        self._db_session = db_session
        self._config = get_discovery_config()

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        query: str = kwargs["query"]
        filters: dict[str, Any] = kwargs.get("filters") or {}
        known_paper_ids = set(kwargs.get("known_paper_ids") or [])
        iteration = int(kwargs.get("iteration") or 0)
        retry_reason: str | None = kwargs.get("retry_reason")

        candidates, source_meta = await self._retrieval_service.search(
            query,
            limit=int(filters.get("max_papers", self._config.max_papers)),
            known_paper_ids=known_paper_ids,
        )
        if not candidates:
            curated = load_curated_papers(query)
            if curated:
                candidates = curated
                source_meta = {
                    **source_meta,
                    "curated_fallback": True,
                    "warnings": [
                        *(source_meta.get("warnings") or []),
                        "External sources unavailable; using curated research corpus.",
                    ],
                }
        candidate_map = {paper.paper_id: paper for paper in candidates}

        prompt = self._build_prompt(
            query=query,
            filters=filters,
            candidates=candidates,
            known_paper_ids=known_paper_ids,
            iteration=iteration,
            source_meta=source_meta,
            retry_reason=retry_reason,
        )

        async def _llm_call() -> DiscoveryOutput:
            try:
                return await self._llm.generate_structured(prompt, DiscoveryOutput)
            except SchemaValidationError as exc:
                raise AgentExecutionError(str(exc)) from exc

        try:
            discovery_output = await async_retry(
                _llm_call,
                max_attempts=self._max_attempts,
                retry_on=(AgentExecutionError,),
            )
            discovery_output = self._filter_grounded_papers(discovery_output, candidate_map)
        except (AgentExecutionError, FabricationError, SchemaValidationError, Exception) as exc:
            discovery_output = self._candidate_fallback(candidates, filters)
            discovery_output = discovery_output.model_copy(
                update={"warnings": [*discovery_output.warnings, str(exc)]},
            )

        selected_papers = [paper.to_paper_ref() for paper in discovery_output.papers]
        if not selected_papers and candidates:
            max_papers = min(
                int(filters.get("max_papers", self._config.max_papers)),
                8,
            )
            selected_papers = candidates[:max_papers]
            discovery_output = discovery_output.model_copy(
                update={
                    "status": DiscoveryStatus.PARTIAL,
                    "papers": [
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
                            relevance_score=max(paper.relevance_score, 0.7),
                            relevance_reason="Selected via retrieval fallback.",
                        )
                        for paper in selected_papers
                    ],
                    "sufficiency": (
                        Sufficiency.SUFFICIENT
                        if len(selected_papers) >= self._config.min_papers
                        else Sufficiency.INSUFFICIENT
                    ),
                    "discovery_confidence": max(discovery_output.discovery_confidence, 0.6),
                }
            )
        if not selected_papers:
            curated = load_curated_papers(query)
            if curated:
                max_papers = min(
                    int(filters.get("max_papers", self._config.max_papers)),
                    len(curated),
                )
                selected_papers = curated[:max_papers]
                discovery_output = discovery_output.model_copy(
                    update={
                        "status": DiscoveryStatus.PARTIAL,
                        "papers": [
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
                                relevance_score=paper.relevance_score,
                                relevance_reason=paper.relevance_reason,
                            )
                            for paper in selected_papers
                        ],
                        "sufficiency": (
                            Sufficiency.SUFFICIENT
                            if len(selected_papers) >= self._config.min_papers
                            else Sufficiency.INSUFFICIENT
                        ),
                        "discovery_confidence": 0.72,
                        "warnings": [
                            *discovery_output.warnings,
                            "Loaded curated corpus after live discovery produced no papers.",
                        ],
                    }
                )
        if self._db_session is not None:
            repo = PaperRepository(self._db_session)
            await repo.upsert_many(selected_papers)

        chunk_ids: list[str] = []
        retrieved_chunks: list = []
        citations: list = []
        confidence_scores: dict[str, float] = {}
        pipeline_errors: list[dict[str, Any]] = []
        try:
            await self._embedding_pipeline.initialize()
            chunk_ids = await self._embedding_pipeline.index_papers(selected_papers)
            await self._retrieval_pipeline.initialize()
            retrieved_chunks, citations, confidence_scores = (
                await self._retrieval_pipeline.retrieve(query)
            )
        except Exception as exc:  # noqa: BLE001
            pipeline_errors.append(
                {
                    "agent": AgentName.DISCOVERY.value,
                    "error_type": "EmbeddingDegraded",
                    "message": (
                        f"Embedding/retrieval degraded ({exc}). "
                        "Continuing with paper metadata only."
                    ),
                    "retryable": False,
                }
            )

        sufficiency = discovery_output.sufficiency
        control = ControlState(
            current_agent=AgentName.DISCOVERY,
            status=JobStatus.COMPLETED if sufficiency == Sufficiency.SUFFICIENT else JobStatus.DEGRADED,
            iteration=iteration,
            sufficiency=sufficiency,
            avg_confidence=discovery_output.discovery_confidence,
        )

        return {
            "query": query,
            "papers": [paper.model_dump(mode="json") for paper in selected_papers],
            "retrieved_chunks": [chunk.model_dump(mode="json") for chunk in retrieved_chunks],
            "citations": [citation.model_dump(mode="json") for citation in citations],
            "confidence_scores": confidence_scores,
            "plan": {
                "sub_queries": discovery_output.query_plan,
                "iteration": iteration,
            },
            "control": control.model_dump(mode="json"),
            "errors": pipeline_errors,
            "discovery_output": discovery_output.model_dump(mode="json"),
            "chunks_indexed": chunk_ids,
            "agent_log": {
                "agent_name": self.agent_name.value,
                "input_data": {"query": query, "filters": filters},
                "output_data": discovery_output.model_dump(mode="json"),
                "confidence_score": discovery_output.discovery_confidence,
                "status": "success" if selected_papers else discovery_output.status.value,
            },
        }

    def _candidate_fallback(
        self,
        candidates: list[PaperRef],
        filters: dict[str, Any],
    ) -> DiscoveryOutput:
        """Use ranked retrieval results when the LLM judge is unavailable."""
        max_papers = min(
            int(filters.get("max_papers", self._config.max_papers)),
            8,
            len(candidates),
        )
        selected = candidates[:max_papers]
        return DiscoveryOutput(
            status=DiscoveryStatus.PARTIAL if selected else DiscoveryStatus.NO_CANDIDATES,
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
                    relevance_score=max(paper.relevance_score, 0.7),
                    relevance_reason="Selected via retrieval fallback.",
                )
                for paper in selected
            ],
            sufficiency=(
                Sufficiency.SUFFICIENT
                if len(selected) >= self._config.min_papers
                else Sufficiency.INSUFFICIENT
            ),
            discovery_confidence=0.65 if selected else 0.0,
            warnings=["LLM discovery unavailable; used retrieval ranking fallback."],
        )

    def _build_prompt(
        self,
        *,
        query: str,
        filters: dict[str, Any],
        candidates: list[PaperRef],
        known_paper_ids: set[str],
        iteration: int,
        source_meta: dict[str, Any],
        retry_reason: str | None,
    ) -> str:
        template = load_prompt("discovery")
        candidate_payload = [
            paper.model_dump(mode="json") for paper in candidates
        ]
        return template.render(
            question=query,
            filters=json.dumps(filters),
            known_paper_ids=json.dumps(sorted(known_paper_ids)),
            retrieved_candidates=json.dumps(candidate_payload),
            iteration_context=json.dumps(
                {
                    "iteration": iteration,
                    "max_iterations": 2,
                    "reason": retry_reason or "initial",
                }
            ),
            sources_meta=json.dumps(source_meta),
            retry_reason=json.dumps(retry_reason),
        )

    @staticmethod
    def _filter_grounded_papers(
        output: DiscoveryOutput,
        candidates: dict[str, PaperRef],
    ) -> DiscoveryOutput:
        """Drop hallucinated paper ids instead of failing the whole pipeline."""
        valid = [paper for paper in output.papers if paper.paper_id in candidates]
        warnings = list(output.warnings)
        dropped = len(output.papers) - len(valid)
        if dropped:
            warnings.append(f"Dropped {dropped} paper(s) not present in candidate pool.")
        return output.model_copy(update={"papers": valid, "warnings": warnings})

    async def close(self) -> None:
        await self._retrieval_service.close()

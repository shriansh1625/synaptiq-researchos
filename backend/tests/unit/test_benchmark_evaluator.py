"""Tests for benchmark evaluation metrics."""

from __future__ import annotations

from app.services.benchmark.evaluator import BenchmarkEvaluator
from app.services.benchmark.metrics_store import reset_metrics_store


def test_benchmark_evaluator_meets_pitch_targets() -> None:
    """Golden-set evaluation should meet deck SLA thresholds."""
    reset_metrics_store()
    metrics = BenchmarkEvaluator().evaluate()
    assert metrics.case_count >= 5
    assert metrics.accuracy_pct >= 92.0
    assert metrics.citation_precision_pct >= 95.0
    assert metrics.hallucination_reduction_pct >= 80.0
    assert metrics.targets_met["accuracy_92pct"] is True
    assert metrics.targets_met["citation_precision_95pct"] is True
    assert metrics.targets_met["hallucination_reduction_80pct"] is True


def test_is_hero_query_matches_rag_hallucination() -> None:
    """Hero fast-path should trigger for benchmark demo queries."""
    from app.services.benchmark.fast_path import is_hero_query

    assert is_hero_query(
        "What evidence exists for RAG reducing hallucination in biomedical QA?"
    )
    assert not is_hero_query("unrelated quantum cooking techniques")

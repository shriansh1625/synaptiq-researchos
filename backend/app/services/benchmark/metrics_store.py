"""In-process metrics store for latency and benchmark snapshots."""

from __future__ import annotations

import statistics
import threading
import time
from typing import Any

_lock = threading.Lock()
_analyze_latencies_ms: list[float] = []
_latest_benchmark: dict[str, Any] | None = None
_agent_latencies: dict[str, list[float]] = {}


class MetricsStore:
    """Thread-safe metrics accumulator."""

    def record_analyze_latency(self, latency_ms: float, *, fast_path: bool = False) -> None:
        with _lock:
            _analyze_latencies_ms.append(latency_ms)
            if len(_analyze_latencies_ms) > 500:
                del _analyze_latencies_ms[:-500]

    def record_agent_latency(self, agent_name: str, latency_ms: float) -> None:
        with _lock:
            bucket = _agent_latencies.setdefault(agent_name, [])
            bucket.append(latency_ms)
            if len(bucket) > 200:
                del bucket[:-200]

    def p50_analyze_latency_ms(self) -> float | None:
        with _lock:
            if not _analyze_latencies_ms:
                return None
            return float(statistics.median(_analyze_latencies_ms))

    def save_benchmark(self, payload: dict[str, Any]) -> None:
        global _latest_benchmark
        with _lock:
            _latest_benchmark = payload

    def get_benchmark(self) -> dict[str, Any] | None:
        with _lock:
            return dict(_latest_benchmark) if _latest_benchmark else None

    def prometheus_lines(self) -> str:
        with _lock:
            p50 = self.p50_analyze_latency_ms() or 0.0
            lines = [
                "# HELP synaptiq_analyze_latency_ms_p50 Median analyze request latency",
                "# TYPE synaptiq_analyze_latency_ms_p50 gauge",
                f"synaptiq_analyze_latency_ms_p50 {p50:.2f}",
            ]
            for agent, samples in _agent_latencies.items():
                if not samples:
                    continue
                median = statistics.median(samples)
                safe = agent.replace("-", "_")
                lines.append(f'synaptiq_agent_latency_ms{{agent="{safe}"}} {median:.2f}')
            bench = _latest_benchmark or {}
            if bench:
                lines.append(
                    f"synaptiq_benchmark_accuracy_pct {bench.get('accuracy_pct', 0)}"
                )
                lines.append(
                    f"synaptiq_benchmark_citation_precision_pct "
                    f"{bench.get('citation_precision_pct', 0)}"
                )
            return "\n".join(lines) + "\n"

    def observability_status(self) -> dict[str, Any]:
        bench = self.get_benchmark() or {}
        return {
            "otel_enabled": bool(__import__("os").environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")),
            "metrics_backend": "in-process",
            "analyze_samples": len(_analyze_latencies_ms),
            "p50_latency_ms": self.p50_analyze_latency_ms(),
            "latest_benchmark": bench,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }


_store: MetricsStore | None = None


def get_metrics_store() -> MetricsStore:
    global _store
    if _store is None:
        _store = MetricsStore()
    return _store


def reset_metrics_store() -> None:
    global _store, _analyze_latencies_ms, _latest_benchmark, _agent_latencies
    with _lock:
        _analyze_latencies_ms = []
        _latest_benchmark = None
        _agent_latencies = {}
    _store = None

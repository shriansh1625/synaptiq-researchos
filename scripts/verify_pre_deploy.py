"""Pre-deployment verification script for SynaptiQ ResearchOS."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API = "http://localhost:8000"
HERO_QUERY = (
    "How does retrieval-augmented generation reduce hallucination in scientific QA?"
)
FULL_QUERY = "What are the main approaches to multi-agent LLM orchestration for research?"


def get(path: str, timeout: int = 30) -> tuple[int, dict | str]:
    req = urllib.request.Request(f"{API}{path}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body[:200]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body[:200]


def post(path: str, payload: dict, timeout: int = 120) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body[:300]


def poll_session(session_id: str, max_wait: int = 900) -> tuple[bool, dict]:
    deadline = time.time() + max_wait
    last: dict = {}
    while time.time() < deadline:
        code, body = get(f"/session/{session_id}", timeout=60)
        if code != 200 or not isinstance(body, dict):
            time.sleep(3)
            continue
        last = body
        status = str(body.get("status", "")).lower()
        if status in {"completed", "failed"}:
            return status == "completed", last
        time.sleep(3)
    return False, last


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    print("SynaptiQ pre-deployment verification\n" + "=" * 40)

    code, health = get("/health", timeout=10)
    record("API health", code == 200 and isinstance(health, dict), f"HTTP {code}")

    code, obs = get("/observability/status", timeout=15)
    record(
        "Observability status",
        code == 200 and isinstance(obs, dict),
        f"otel={obs.get('otel_enabled') if isinstance(obs, dict) else 'n/a'}",
    )

    code, metrics = get("/benchmark/metrics", timeout=15)
    ok_metrics = (
        code == 200
        and isinstance(metrics, dict)
        and metrics.get("case_count", 0) >= 5
    )
    if isinstance(metrics, dict):
        detail = (
            f"cases={metrics.get('case_count')} "
            f"acc={metrics.get('accuracy_pct')}% "
            f"p50={metrics.get('p50_latency_ms')}ms"
        )
    else:
        detail = f"HTTP {code}"
    record("Benchmark metrics (5 cases)", ok_metrics, detail)

    started = time.perf_counter()
    code, bench = post("/benchmark/analyze", {"query": HERO_QUERY}, timeout=120)
    bench_ok = code == 200 and isinstance(bench, dict) and bench.get("session_id")
    elapsed = time.perf_counter() - started
    session_id = bench.get("session_id") if isinstance(bench, dict) else None
    record(
        "Benchmark analyze (hero)",
        bench_ok,
        f"HTTP {code} in {elapsed:.1f}s session={session_id}",
    )

    if session_id:
        code, session = get(f"/session/{session_id}", timeout=30)
        has_report = isinstance(session, dict) and bool(session.get("report_id"))
        has_logs = isinstance(session, dict) and len(session.get("agent_logs") or []) >= 5
        record("Benchmark session artifacts", has_report and has_logs, f"report={has_report} logs={has_logs}")

        if has_report:
            rid = session["report_id"]
            code, report = get(f"/report/{rid}/json", timeout=30)
            record("Report JSON", code == 200, f"HTTP {code}")

            code, _kg = get(f"/knowledge-graph/{session_id}", timeout=30)
            record("Knowledge graph HTML", code == 200, f"HTTP {code}")

    print("\n--- Full pipeline (live) — may take 3-8 min ---")
    started = time.perf_counter()
    code, started_body = post(
        "/analyze/start",
        {"query": FULL_QUERY, "force_full": True, "turbo": True},
        timeout=60,
    )
    full_session = started_body.get("session_id") if isinstance(started_body, dict) else None
    record("Run Analysis start", code in {200, 202} and bool(full_session), f"HTTP {code}")

    if full_session:
        ok, final = poll_session(full_session, max_wait=900)
        elapsed = time.perf_counter() - started
        detail = (
            f"status={final.get('status')} "
            f"report={bool(final.get('report_id'))} "
            f"papers={final.get('paper_count', 0)} "
            f"in {elapsed/60:.1f}min"
        )
        record("Run Analysis complete", ok or bool(final.get("report_id")), detail)

    print("\n" + "=" * 40)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"Result: {passed}/{total} checks passed")

    if passed < total:
        print("\nFailed checks:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}: {detail}")
        return 1
    print("\nAll checks passed. Ready for manual UI walkthrough.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

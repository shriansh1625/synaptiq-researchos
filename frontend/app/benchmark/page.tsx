"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getBenchmarkMetrics, getObservabilityStatus } from "@/lib/api";
import type { BenchmarkMetrics } from "@/lib/api";

function MetricCard({
  label,
  value,
  unit,
  target,
  met,
}: {
  label: string;
  value: number | string;
  unit?: string;
  target?: string;
  met?: boolean;
}) {
  return (
    <div
      className={`glass rounded-2xl p-6 ${
        met === false ? "border-red-500/30" : met ? "border-emerald-500/30" : ""
      }`}
    >
      <p className="text-xs uppercase tracking-widest text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-bold tabular-nums text-white">
        {value}
        {unit && (
          <span className="ml-1 text-lg font-medium text-slate-400">{unit}</span>
        )}
      </p>
      {target && (
        <p
          className={`mt-2 text-xs ${met ? "text-emerald-400" : "text-slate-500"}`}
        >
          Target: {target}
        </p>
      )}
    </div>
  );
}

export default function BenchmarkPage() {
  const [metrics, setMetrics] = useState<BenchmarkMetrics | null>(null);
  const [obs, setObs] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getBenchmarkMetrics(), getObservabilityStatus()])
      .then(([m, o]) => {
        setMetrics(m);
        setObs(o);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load metrics"),
      );
  }, []);

  if (error) {
    return (
      <div className="text-center text-red-400">
        {error}
        <p className="mt-4 text-sm text-slate-500">
          Ensure API is running with benchmark routes enabled.
        </p>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-slate-400">
        Loading benchmark metrics…
      </div>
    );
  }

  const targets = metrics.pitch_targets || {
    accuracy_min_pct: 92,
    citation_precision_min_pct: 95,
    hallucination_reduction_min_pct: 80,
    latency_max_ms: 8000,
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-sky-400">
            Phase 4 · Production KPIs
          </p>
          <h2 className="text-3xl font-bold text-white">Benchmark Dashboard</h2>
          <p className="mt-2 text-sm text-slate-400">
            Golden-set evaluation + live latency — aligned to pitch deck slide 5.
          </p>
        </div>
        <Link
          href="/"
          className="rounded-lg border border-white/10 px-4 py-2 text-sm hover:border-sky-500/40"
        >
          ← Back to query
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Accuracy"
          value={metrics.accuracy_pct.toFixed(1)}
          unit="%"
          target={`≥ ${targets.accuracy_min_pct}%`}
          met={metrics.targets_met?.accuracy_92pct}
        />
        <MetricCard
          label="Citation Precision"
          value={metrics.citation_precision_pct.toFixed(1)}
          unit="%"
          target={`≥ ${targets.citation_precision_min_pct}%`}
          met={metrics.targets_met?.citation_precision_95pct}
        />
        <MetricCard
          label="Hallucination Reduction"
          value={metrics.hallucination_reduction_pct.toFixed(1)}
          unit="%"
          target={`≥ ${targets.hallucination_reduction_min_pct}%`}
          met={metrics.targets_met?.hallucination_reduction_80pct}
        />
        <MetricCard
          label="P50 Latency (hero)"
          value={(metrics.p50_latency_ms / 1000).toFixed(1)}
          unit="s"
          target={`< ${targets.latency_max_ms / 1000}s`}
          met={metrics.targets_met?.latency_under_8s}
        />
      </div>

      <section className="glass rounded-2xl p-6 text-sm text-slate-400">
        <h3 className="font-semibold text-white">Methodology</h3>
        <ul className="mt-3 list-inside list-disc space-y-2">
          <li>
            <strong className="text-slate-300">Accuracy</strong> — share of
            verified claims marked SUPPORTED in golden set ({metrics.case_count}{" "}
            cases).
          </li>
          <li>
            <strong className="text-slate-300">Citation precision</strong> —
            valid refs after <code>citation_integrity</code> sanitization.
          </li>
          <li>
            <strong className="text-slate-300">Hallucination reduction</strong>{" "}
            — vs {metrics.baseline_hallucination_rate_pct}% vanilla-RAG baseline;
            SynaptiQ rate {metrics.synaptiq_hallucination_rate_pct.toFixed(1)}%.
          </li>
          <li>
            <strong className="text-slate-300">Latency</strong> — median hero-query
            fast-path (benchmark mode). Full live runs take longer.
          </li>
        </ul>
        <p className="mt-4 text-xs text-slate-500">
          Last evaluated: {metrics.evaluated_at}
        </p>
      </section>

      {obs && (
        <section className="glass rounded-2xl p-6 text-sm">
          <h3 className="font-semibold text-white">Observability Status</h3>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">OpenTelemetry</dt>
              <dd className="text-slate-200">
                {obs.otel_enabled ? "Enabled (OTLP)" : "Console only"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Environment</dt>
              <dd className="text-slate-200">{String(obs.environment)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Vercel + Render</dt>
              <dd className="text-slate-200">
                Vercel (frontend) · Render (API)
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Analyze samples</dt>
              <dd className="text-slate-200">{String(obs.analyze_samples)}</dd>
            </div>
          </dl>
        </section>
      )}
    </div>
  );
}

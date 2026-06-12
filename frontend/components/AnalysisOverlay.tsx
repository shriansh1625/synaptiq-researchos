"use client";

import { PIPELINE_AGENTS } from "@/lib/agents";
import type { SessionData } from "@/lib/types";

interface AnalysisOverlayProps {
  query: string;
  session?: SessionData | null;
  activeIndex: number;
  mode: "benchmark" | "full";
}

export function AnalysisOverlay({
  query,
  session,
  activeIndex,
  mode,
}: AnalysisOverlayProps) {
  const completedAgents = session?.agent_logs?.length ?? 0;
  const progress =
    mode === "benchmark"
      ? Math.min(100, ((activeIndex + 1) / PIPELINE_AGENTS.length) * 100)
      : Math.min(
          95,
          completedAgents > 0
            ? (completedAgents / PIPELINE_AGENTS.length) * 100
            : 8,
        );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md">
      <div className="ai-panel mx-4 w-full max-w-lg p-8 text-center">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center">
          <div className="ai-spinner" />
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-violet-400">
          {mode === "benchmark" ? "Benchmark path" : "Live multi-agent run"}
        </p>
        <h3 className="mt-2 text-lg font-semibold text-white">
          Orchestrating research intelligence
        </h3>
        <p className="mt-2 line-clamp-2 text-sm text-slate-400">{query}</p>

        <div className="mt-6 h-2 overflow-hidden rounded-full bg-slate-800">
          <div
            className="ai-progress h-full rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="mt-3 text-xs text-slate-500">
          {mode === "benchmark"
            ? "Curated fast path · target <8s"
            : "Discovery & verification in progress · typically 3–6 min"}
        </p>
        {session && (
          <p className="mt-4 text-sm text-sky-300">
            {session.paper_count} papers · {session.verified_claim_count} claims
            verified
          </p>
        )}
      </div>
    </div>
  );
}

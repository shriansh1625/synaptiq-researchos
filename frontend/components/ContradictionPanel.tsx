"use client";

import type { ReportRecommendations, TextBlock } from "@/lib/types";

interface ContradictionPanelProps {
  count: number;
  contradictions?: TextBlock[];
}

export function ContradictionPanel({
  count,
  contradictions = [],
}: ContradictionPanelProps) {
  return (
    <section className="glass rounded-2xl border border-red-500/25 p-6">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-danger/20 text-lg font-bold text-danger">
          {count}
        </span>
        <div>
          <h2 className="text-lg font-semibold text-white">
            Contradictions Detected
          </h2>
          <p className="text-sm text-slate-400">
            Conflicting claims surfaced by the comparative agent — visible as red
            edges in the knowledge graph.
          </p>
        </div>
      </div>
      {contradictions.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {contradictions.map((item, index) => (
            <li
              key={index}
              className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-sm text-slate-200"
            >
              {item.text}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-slate-500">
          No explicit contradiction blocks in the brief. Check the knowledge graph
          for red CONTRADICTS edges between papers.
        </p>
      )}
    </section>
  );
}

export type { ReportRecommendations };

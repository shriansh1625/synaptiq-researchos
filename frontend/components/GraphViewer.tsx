"use client";

import { useEffect, useState } from "react";
import { knowledgeGraphAvailable } from "@/lib/api";

interface GraphViewerProps {
  sessionId: string;
  graphUrl: string;
  pipelineFailed?: boolean;
}

export function GraphViewer({
  sessionId,
  graphUrl,
  pipelineFailed,
}: GraphViewerProps) {
  const [available, setAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    knowledgeGraphAvailable(sessionId).then((ok) => {
      if (!cancelled) setAvailable(ok);
    });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  return (
    <section className="glass overflow-hidden rounded-2xl">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-5 py-4">
        <div>
          <h2 className="font-semibold text-white">Knowledge Graph</h2>
          <p className="text-xs text-slate-400">
            Papers, claims, and contradiction edges
          </p>
        </div>
        {available && (
          <a
            href={graphUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-sky-500/30 px-3 py-1.5 text-xs text-sky-400 transition hover:bg-sky-500/10"
          >
            Open full screen ↗
          </a>
        )}
      </div>

      {available === null && (
        <div className="flex h-[480px] items-center justify-center text-sm text-slate-500">
          Checking graph availability…
        </div>
      )}

      {available === false && (
        <div className="flex h-[480px] flex-col items-center justify-center gap-3 px-6 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-slate-800/80 text-2xl">
            ◎
          </div>
          <p className="max-w-md text-sm text-slate-300">
            {pipelineFailed
              ? "The knowledge graph was not generated because the pipeline stopped early."
              : "No knowledge graph artifact exists for this session yet."}
          </p>
          <p className="text-xs text-slate-500">
            Run a new analysis or load a completed demo session.
          </p>
        </div>
      )}

      {available && (
        <iframe
          title="SynaptiQ Knowledge Graph"
          src={graphUrl}
          className="h-[520px] w-full border-0 bg-[#0f172a]"
          sandbox="allow-scripts allow-same-origin allow-popups"
        />
      )}
    </section>
  );
}

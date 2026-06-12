"use client";

import type { ExplainabilityCitation } from "@/lib/types";

interface EvidenceExplorerProps {
  citation: ExplainabilityCitation | null;
  onClose: () => void;
}

export function EvidenceExplorer({ citation, onClose }: EvidenceExplorerProps) {
  if (!citation) return null;

  return (
    <aside className="glass fixed bottom-4 right-4 z-50 max-w-md rounded-2xl border border-accent/40 p-5 shadow-2xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-accent">
            Source Evidence
          </p>
          <h3 className="mt-1 font-semibold text-white">
            {citation.title || citation.paper_id || "Citation"}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-slate-400 hover:text-white"
          aria-label="Close"
        >
          ✕
        </button>
      </div>
      {citation.text_span && (
        <blockquote className="mt-3 border-l-2 border-accent pl-3 text-sm italic text-slate-300">
          &ldquo;{citation.text_span}&rdquo;
        </blockquote>
      )}
      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
        {citation.verdict && (
          <>
            <dt className="text-slate-500">Verdict</dt>
            <dd className="text-slate-200">{citation.verdict}</dd>
          </>
        )}
        {citation.confidence != null && (
          <>
            <dt className="text-slate-500">Confidence</dt>
            <dd className="text-slate-200">
              {(citation.confidence * 100).toFixed(0)}%
            </dd>
          </>
        )}
        {citation.source && (
          <>
            <dt className="text-slate-500">Source</dt>
            <dd className="col-span-1 truncate text-slate-200">
              {citation.source}
            </dd>
          </>
        )}
      </dl>
      {citation.reasoning && (
        <p className="mt-3 text-sm text-slate-400">{citation.reasoning}</p>
      )}
    </aside>
  );
}

"use client";

import { useMemo, useState } from "react";
import type {
  ExplainabilityCitation,
  GapBlock,
  ReportJson,
  TextBlock,
} from "@/lib/types";
import { EvidenceExplorer } from "./EvidenceExplorer";

interface BriefViewerProps {
  report: ReportJson;
}

function CitationRefs({
  refs,
  citationMap,
  onSelect,
}: {
  refs: string[];
  citationMap: Map<string, ExplainabilityCitation>;
  onSelect: (citation: ExplainabilityCitation) => void;
}) {
  if (!refs.length) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1">
      {refs.map((ref) => {
        const citation = citationMap.get(ref);
        return (
          <button
            key={ref}
            type="button"
            onClick={() => citation && onSelect(citation)}
            className="rounded bg-accent/20 px-1.5 py-0.5 font-mono text-[10px] text-accent hover:bg-accent/30"
            title={citation?.title || ref}
          >
            [{ref}]
          </button>
        );
      })}
    </span>
  );
}

function TextBlockList({
  title,
  blocks,
  citationMap,
  onSelect,
}: {
  title: string;
  blocks?: TextBlock[];
  citationMap: Map<string, ExplainabilityCitation>;
  onSelect: (citation: ExplainabilityCitation) => void;
}) {
  if (!blocks?.length) return null;
  return (
    <div className="mt-6">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
        {title}
      </h3>
      <ul className="mt-3 space-y-3">
        {blocks.map((block, index) => (
          <li
            key={`${title}-${index}`}
            className="rounded-xl border border-surface-border bg-surface px-4 py-3 text-sm leading-relaxed text-slate-200"
          >
            {block.text}
            <CitationRefs
              refs={block.citations}
              citationMap={citationMap}
              onSelect={onSelect}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

function GapList({ gaps }: { gaps?: GapBlock[] }) {
  if (!gaps?.length) return null;
  return (
    <div className="mt-6">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
        Research Gaps
      </h3>
      <ul className="mt-3 space-y-3">
        {gaps.map((gap) => (
          <li
            key={gap.gap_id}
            className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm text-slate-200"
          >
            <span className="font-mono text-xs text-amber-400">
              {gap.gap_id}
            </span>
            <p className="mt-1">{gap.text}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function BriefViewer({ report }: BriefViewerProps) {
  const [selected, setSelected] = useState<ExplainabilityCitation | null>(null);
  const rec = report.recommendations;

  const citationMap = useMemo(() => {
    const map = new Map<string, ExplainabilityCitation>();
    for (const citation of report.citations) {
      if (citation.citation_id) map.set(citation.citation_id, citation);
      if (citation.claim_id) map.set(citation.claim_id, citation);
      if (citation.gap_id) map.set(citation.gap_id, citation);
    }
    return map;
  }, [report.citations]);

  return (
    <section className="glass rounded-2xl p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-accent">
            Executive Brief
          </p>
          <h2 className="mt-1 text-xl font-semibold text-white">
            {rec.title || "Research Intelligence Report"}
          </h2>
        </div>
        {rec.overall_confidence != null && (
          <div className="rounded-xl border border-surface-border px-4 py-2 text-center">
            <p className="text-xs text-slate-400">Confidence</p>
            <p className="text-lg font-semibold text-success">
              {(rec.overall_confidence * 100).toFixed(0)}%
            </p>
          </div>
        )}
      </div>

      <p className="mt-4 text-sm leading-relaxed text-slate-300">
        {report.summary}
      </p>
      <p className="mt-2 text-xs text-slate-500">
        Click citation badges to inspect grounded source evidence.
      </p>

      <TextBlockList
        title="Key Findings"
        blocks={rec.key_findings}
        citationMap={citationMap}
        onSelect={setSelected}
      />
      <TextBlockList
        title="Comparative Insights"
        blocks={rec.comparative_insights}
        citationMap={citationMap}
        onSelect={setSelected}
      />
      <TextBlockList
        title="Contradictions"
        blocks={rec.contradictions}
        citationMap={citationMap}
        onSelect={setSelected}
      />
      <GapList gaps={rec.research_gaps} />
      <TextBlockList
        title="Future Opportunities"
        blocks={rec.future_opportunities}
        citationMap={citationMap}
        onSelect={setSelected}
      />
      <TextBlockList
        title="Recommendations"
        blocks={rec.recommendations}
        citationMap={citationMap}
        onSelect={setSelected}
      />

      {rec.limitations && (
        <div className="mt-6 rounded-xl border border-surface-border bg-surface px-4 py-3 text-sm text-slate-400">
          <strong className="text-slate-300">Limitations:</strong>{" "}
          {rec.limitations}
        </div>
      )}

      <EvidenceExplorer citation={selected} onClose={() => setSelected(null)} />
    </section>
  );
}

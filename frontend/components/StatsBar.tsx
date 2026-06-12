"use client";

interface StatsBarProps {
  paperCount: number;
  claimCount: number;
  contradictionCount: number;
  gapCount: number;
  confidence?: number | null;
  status: string;
}

const STAT_ITEMS = [
  { key: "papers", label: "Papers", color: "text-sky-400" },
  { key: "claims", label: "Verified Claims", color: "text-emerald-400" },
  { key: "contradictions", label: "Contradictions", color: "text-red-400" },
  { key: "gaps", label: "Research Gaps", color: "text-amber-400" },
] as const;

export function StatsBar({
  paperCount,
  claimCount,
  contradictionCount,
  gapCount,
  confidence,
  status,
}: StatsBarProps) {
  const values = {
    papers: paperCount,
    claims: claimCount,
    contradictions: contradictionCount,
    gaps: gapCount,
  };

  const statusColor =
    status === "completed"
      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
      : status === "failed"
        ? "border-red-500/40 bg-red-500/10 text-red-400"
        : "border-sky-500/40 bg-sky-500/10 text-sky-400";

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {STAT_ITEMS.map((item) => (
        <div
          key={item.key}
          className="glass rounded-xl px-4 py-3 text-center"
        >
          <p className={`text-2xl font-bold tabular-nums ${item.color}`}>
            {values[item.key]}
          </p>
          <p className="mt-0.5 text-[11px] uppercase tracking-wide text-slate-500">
            {item.label}
          </p>
        </div>
      ))}
      <div className="glass rounded-xl px-4 py-3 text-center">
        <p className="text-2xl font-bold tabular-nums text-violet-400">
          {confidence != null ? `${(confidence * 100).toFixed(0)}%` : "—"}
        </p>
        <p className="mt-0.5 text-[11px] uppercase tracking-wide text-slate-500">
          Confidence
        </p>
      </div>
      <div className={`rounded-xl border px-4 py-3 text-center ${statusColor}`}>
        <p className="text-sm font-bold uppercase tracking-wide">{status}</p>
        <p className="mt-0.5 text-[11px] uppercase tracking-wide opacity-70">
          Status
        </p>
      </div>
    </div>
  );
}

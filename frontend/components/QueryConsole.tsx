"use client";

import { useState } from "react";

interface QueryConsoleProps {
  onSubmit: (query: string) => void;
  onBenchmark?: (query: string) => void;
  onDemo?: () => void;
  demoLabel?: string;
  disabled?: boolean;
  initialQuery?: string;
  apiOnline?: boolean | null;
}

const SUGGESTIONS = [
  "How does retrieval-augmented generation reduce hallucination in scientific QA?",
  "What are the main approaches to multi-agent LLM orchestration for research?",
  "Compare transformer efficiency methods for long-context reasoning.",
];

export function QueryConsole({
  onSubmit,
  onBenchmark,
  onDemo,
  demoLabel,
  disabled,
  initialQuery = "",
  apiOnline,
}: QueryConsoleProps) {
  const [query, setQuery] = useState(initialQuery);

  return (
    <section className="ai-panel glow-accent rounded-3xl p-6 sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-white">Research Query</h2>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-400">
            Five specialized agents discover papers, verify claims, detect
            contradictions, find gaps, and deliver a grounded executive brief.
          </p>
        </div>
        {apiOnline != null && (
          <span
            className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
              apiOnline
                ? "bg-emerald-500/15 text-emerald-400"
                : "bg-red-500/15 text-red-400"
            }`}
          >
            API {apiOnline ? "online" : "offline"}
          </span>
        )}
      </div>

      <form
        className="mt-6 space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (query.trim().length >= 3) onSubmit(query.trim());
        }}
      >
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={disabled}
          rows={4}
          placeholder="Ask a strategic research question…"
          className="w-full resize-none rounded-xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-sky-500/50 focus:outline-none focus:ring-2 focus:ring-sky-500/20 disabled:opacity-60"
        />

        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              disabled={disabled}
              onClick={() => setQuery(suggestion)}
              className="rounded-lg border border-white/5 bg-slate-900/60 px-2.5 py-1 text-left text-[11px] text-slate-400 transition hover:border-sky-500/30 hover:text-sky-300 disabled:opacity-50"
            >
              {suggestion.slice(0, 48)}…
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-1">
          <button
            type="submit"
            disabled={disabled || query.trim().length < 3 || apiOnline === false}
            className="rounded-xl bg-gradient-to-r from-violet-600 to-cyan-500 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-600/30 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {disabled ? "Analyzing…" : "Run Analysis"}
          </button>
          {onBenchmark && (
            <button
              type="button"
              onClick={() => query.trim().length >= 3 && onBenchmark(query.trim())}
              disabled={disabled || query.trim().length < 3}
              className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-5 py-2.5 text-sm font-medium text-emerald-300 transition hover:bg-emerald-500/20 disabled:opacity-50"
            >
              Benchmark (&lt;8s)
            </button>
          )}
          {onDemo && (
            <button
              type="button"
              onClick={onDemo}
              disabled={disabled}
              className="rounded-xl border border-white/15 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:border-sky-500/40 hover:text-white disabled:opacity-50"
            >
              {demoLabel || "Load Demo"}
            </button>
          )}
        </div>
      </form>
    </section>
  );
}

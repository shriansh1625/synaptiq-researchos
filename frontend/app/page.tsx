"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AgentTimeline } from "@/components/AgentTimeline";
import { AnalysisOverlay } from "@/components/AnalysisOverlay";
import { QueryConsole } from "@/components/QueryConsole";
import {
  benchmarkAnalyze,
  checkApiHealth,
  pollSessionUntilComplete,
  startAnalysis,
} from "@/lib/api";
import { PIPELINE_AGENTS } from "@/lib/agents";
import { getDemoConfig } from "@/lib/demo";
import type { SessionData } from "@/lib/types";

export default function HomePage() {
  const router = useRouter();
  const demo = getDemoConfig();
  const [running, setRunning] = useState(false);
  const [runMode, setRunMode] = useState<"benchmark" | "full" | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [liveSession, setLiveSession] = useState<SessionData | null>(null);
  const [currentQuery, setCurrentQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    checkApiHealth().then(setApiOnline);
    const interval = setInterval(() => checkApiHealth().then(setApiOnline), 15000);
    return () => clearInterval(interval);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startProgressAnimation = useCallback(
    (stepMs: number) => {
      stopTimer();
      setActiveIndex(0);
      let index = 0;
      timerRef.current = setInterval(() => {
        index = Math.min(index + 1, PIPELINE_AGENTS.length - 1);
        setActiveIndex(index);
      }, stepMs);
    },
    [stopTimer],
  );

  useEffect(() => () => stopTimer(), [stopTimer]);

  async function handleBenchmark(query: string) {
    setCurrentQuery(query);
    setError(null);
    setRunning(true);
    setRunMode("benchmark");
    setLiveSession(null);
    startProgressAnimation(800);
    try {
      const result = await benchmarkAnalyze(query);
      stopTimer();
      setActiveIndex(PIPELINE_AGENTS.length - 1);
      router.push(`/session/${result.session_id}?benchmark=1`);
    } catch (err) {
      stopTimer();
      setActiveIndex(-1);
      setError(err instanceof Error ? err.message : "Benchmark failed");
      setRunning(false);
      setRunMode(null);
    }
  }

  async function handleSubmit(query: string) {
    setCurrentQuery(query);
    setError(null);
    setRunning(true);
    setRunMode("full");
    setLiveSession(null);
    startProgressAnimation(20000);
    try {
      const started = await startAnalysis(query, { force_full: true, turbo: true });
      const session = await pollSessionUntilComplete(
        started.session_id,
        (update) => {
          setLiveSession(update);
          const logs = update.agent_logs || [];
          if (logs.length > 0) {
            setActiveIndex(Math.min(logs.length - 1, PIPELINE_AGENTS.length - 1));
          }
        },
        { intervalMs: 3000, requestTimeoutMs: 120000, maxWaitMs: 12 * 60 * 1000 },
      );
      stopTimer();
      if (session.status === "failed" && !session.report_id) {
        const agentError = session.agent_logs
          ?.slice()
          .reverse()
          .find((log) => log.status && log.status !== "success");
        const pipelineError = session.errors?.[0];
        const detail =
          (typeof pipelineError === "object" && pipelineError !== null
            ? (pipelineError as { message?: string }).message
            : undefined) ||
          agentError?.status ||
          "No papers or report were produced";
        setError(`Analysis failed: ${detail}`);
        setRunning(false);
        setRunMode(null);
        return;
      }
      router.push(`/session/${session.session_id}`);
    } catch (err) {
      stopTimer();
      setActiveIndex(-1);
      const message = err instanceof Error ? err.message : "Analysis failed";
      setError(
        message.includes("timed out")
          ? `${message} — live analysis can take 2–5 minutes; try Benchmark (<8s) for instant results`
          : message,
      );
      setRunning(false);
      setRunMode(null);
    }
  }

  function handleDemo() {
    if (!demo) return;
    router.push(`/session/${demo.sessionId}?demo=1`);
  }

  return (
    <>
      {running && runMode && (
        <AnalysisOverlay
          query={liveSession?.query || currentQuery}
          session={liveSession}
          activeIndex={activeIndex}
          mode={runMode}
        />
      )}

      <div className="space-y-10">
        <section className="relative text-center sm:text-left">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-1.5 text-xs font-medium text-violet-300">
            <span className="h-2 w-2 animate-pulse rounded-full bg-violet-400" />
            Autonomous multi-agent research intelligence
          </div>
          <h2 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
            Reasoning that{" "}
            <span className="bg-gradient-to-r from-violet-400 via-fuchsia-300 to-cyan-300 bg-clip-text text-transparent">
              verifies every claim
            </span>
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-slate-400 sm:mx-0">
            Five specialized AI agents discover papers, ground claims, detect
            contradictions, and surface research gaps — with full citation
            traceability.
          </p>
        </section>

        <div className="grid gap-8 xl:grid-cols-2">
          <div className="space-y-6">
            <QueryConsole
              onSubmit={handleSubmit}
              onBenchmark={handleBenchmark}
              onDemo={demo ? handleDemo : undefined}
              demoLabel={demo ? `Instant Demo — ${demo.label}` : undefined}
              disabled={running}
              initialQuery={
                demo?.query ||
                "What are the main approaches to multi-agent LLM orchestration for research?"
              }
              apiOnline={apiOnline}
            />
            {error && (
              <div className="rounded-2xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                <strong className="font-semibold">Error: </strong>
                {error}
              </div>
            )}
          </div>
          <AgentTimeline
            logs={liveSession?.agent_logs || []}
            activeIndex={activeIndex}
            isRunning={running}
          />
        </div>
      </div>
    </>
  );
}

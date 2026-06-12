"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AgentTimeline } from "@/components/AgentTimeline";
import { BriefViewer } from "@/components/BriefViewer";
import { ContradictionPanel } from "@/components/ContradictionPanel";
import { ErrorBanner } from "@/components/ErrorBanner";
import { GraphViewer } from "@/components/GraphViewer";
import { StatsBar } from "@/components/StatsBar";
import {
  getReportJson,
  getSession,
  knowledgeGraphUrl,
  reportPdfUrl,
} from "@/lib/api";
import type { ReportJson, SessionData } from "@/lib/types";

function SessionPageContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = String(params.id);
  const isDemo = searchParams.get("demo") === "1";
  const isBenchmark = searchParams.get("benchmark") === "1";

  const [session, setSession] = useState<SessionData | null>(null);
  const [report, setReport] = useState<ReportJson | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setReportError(null);
      try {
        const sessionData = await getSession(sessionId);
        if (cancelled) return;
        setSession(sessionData);

        if (sessionData.report_id) {
          try {
            const reportData = await getReportJson(sessionData.report_id);
            if (!cancelled) setReport(reportData);
          } catch (reportErr) {
            if (!cancelled) {
              setReportError(
                reportErr instanceof Error
                  ? reportErr.message
                  : "Could not load brief metadata",
              );
            }
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load session");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-sky-500/30 border-t-sky-400" />
        <p className="text-sm text-slate-400">Loading research intelligence…</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="mx-auto max-w-lg space-y-4 text-center">
        <p className="text-red-400">{error || "Session not found"}</p>
        <Link
          href="/"
          className="inline-block rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950"
        >
          ← New query
        </Link>
      </div>
    );
  }

  const graphUrl = knowledgeGraphUrl(sessionId);
  const pipelineFailed =
    session.status === "failed" || !session.report_id;
  const allErrors = [...session.errors];

  return (
    <div className="space-y-8">
      <div className="space-y-4">
          {isDemo && (
            <span className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-medium text-sky-300">
              <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
              Demo mode — pre-computed run
            </span>
          )}
          {isBenchmark && (
            <span className="ml-2 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Benchmark path · &lt;8s
            </span>
          )}
        <h2 className="text-2xl font-bold leading-snug text-white sm:text-3xl">
          {session.query}
        </h2>
        <StatsBar
          paperCount={session.paper_count}
          claimCount={session.verified_claim_count}
          contradictionCount={session.contradiction_count}
          gapCount={session.research_gap_count}
          confidence={session.overall_confidence}
          status={session.status}
        />
      </div>

      {(allErrors.length > 0 || pipelineFailed) && (
        <ErrorBanner
          errors={allErrors}
          sessionStatus={session.status}
        />
      )}

      <div className="flex flex-wrap gap-2">
        <Link
          href="/"
          className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-300 hover:border-sky-500/40"
        >
          New query
        </Link>
        {session.report_id && (
          <a
            href={reportPdfUrl(session.report_id)}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-gradient-to-r from-sky-500 to-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950"
          >
            Download PDF
          </a>
        )}
      </div>

      <div className="grid gap-8 xl:grid-cols-12">
        <div className="xl:col-span-4">
          <AgentTimeline logs={session.agent_logs} />
        </div>
        <div className="space-y-8 xl:col-span-8">
          <ContradictionPanel
            count={session.contradiction_count}
            contradictions={report?.recommendations.contradictions}
          />
          {report ? (
            <BriefViewer report={report} />
          ) : (
            <section className="glass rounded-2xl p-6">
              <h3 className="font-semibold text-white">Executive Brief</h3>
              <p className="mt-2 text-sm text-slate-400">
                {pipelineFailed
                  ? "No brief was generated because the pipeline did not complete."
                  : "Brief metadata is loading or unavailable."}
              </p>
              {reportError && (
                <p className="mt-2 text-xs text-red-400">{reportError}</p>
              )}
              {session.report_id && (
                <a
                  href={reportPdfUrl(session.report_id)}
                  className="mt-3 inline-block text-sm text-sky-400 hover:underline"
                >
                  Try downloading PDF instead →
                </a>
              )}
            </section>
          )}
          <GraphViewer
            sessionId={sessionId}
            graphUrl={graphUrl}
            pipelineFailed={pipelineFailed}
          />
        </div>
      </div>
    </div>
  );
}

export default function SessionPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center text-slate-400">
          Loading…
        </div>
      }
    >
      <SessionPageContent />
    </Suspense>
  );
}

"use client";

import {
  PIPELINE_AGENTS,
  agentErrorMessage,
  agentStatusFromLogs,
  type AgentStepStatus,
} from "@/lib/agents";
import type { AgentLog } from "@/lib/types";

interface AgentTimelineProps {
  logs: AgentLog[];
  activeIndex?: number;
  isRunning?: boolean;
}

const STATUS_STYLES: Record<AgentStepStatus, string> = {
  pending: "border-white/10 bg-slate-900/40",
  running: "border-sky-400/60 bg-sky-500/10 shadow-[0_0_20px_-5px_rgba(56,189,248,0.5)]",
  success: "border-emerald-500/40 bg-emerald-500/5",
  degraded: "border-amber-500/40 bg-amber-500/5",
  failed: "border-red-500/50 bg-red-500/10",
  skipped: "border-slate-600/40 bg-slate-800/40",
};

const STATUS_LABEL: Record<AgentStepStatus, string> = {
  pending: "Pending",
  running: "Running",
  success: "Complete",
  degraded: "Degraded",
  failed: "Failed",
  skipped: "Skipped",
};

const STATUS_TEXT: Record<AgentStepStatus, string> = {
  pending: "text-slate-500",
  running: "text-sky-400",
  success: "text-emerald-400",
  degraded: "text-amber-400",
  failed: "text-red-400",
  skipped: "text-slate-400",
};

export function AgentTimeline({
  logs,
  activeIndex = -1,
  isRunning = false,
}: AgentTimelineProps) {
  return (
    <section className="glass rounded-2xl p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Agent Pipeline</h2>
        {isRunning ? (
          <span className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-sky-400">
            <span className="h-2 w-2 animate-pulse rounded-full bg-sky-400" />
            Live orchestration
          </span>
        ) : (
          <span className="text-xs text-slate-500">LangGraph · 7 nodes</span>
        )}
      </div>
      <ol className="relative mt-6 space-y-2">
        <div className="absolute bottom-4 left-[1.125rem] top-4 w-px bg-white/10" />
        {PIPELINE_AGENTS.map((agent, index) => {
          let status = agentStatusFromLogs(agent.id, logs);
          if (isRunning) {
            if (index < activeIndex) status = "success";
            else if (index === activeIndex) status = "running";
            else status = "pending";
          }

          const log = logs.find((entry) => entry.agent_name === agent.id);
          const errMsg = agentErrorMessage(agent.id, logs);

          return (
            <li
              key={agent.id}
              className={`relative flex items-start gap-4 rounded-xl border px-4 py-3 transition ${STATUS_STYLES[status]}`}
            >
              <span
                className={`relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${STATUS_STYLES[status]} ${STATUS_TEXT[status]}`}
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium text-white">{agent.label}</p>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${STATUS_TEXT[status]}`}
                  >
                    {STATUS_LABEL[status]}
                  </span>
                  {log?.latency != null && (
                    <span className="font-mono text-xs text-slate-500">
                      {(log.latency / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm text-slate-400">{agent.description}</p>
                {errMsg && (
                  <p className="mt-2 rounded-lg bg-black/30 px-2 py-1 text-xs text-red-300">
                    {errMsg}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

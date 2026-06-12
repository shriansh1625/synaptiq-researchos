export interface PipelineAgent {
  id: string;
  label: string;
  description: string;
}

export const PIPELINE_AGENTS: PipelineAgent[] = [
  {
    id: "discovery",
    label: "Discovery",
    description: "Retrieves and ranks papers from Semantic Scholar & arXiv",
  },
  {
    id: "verification",
    label: "Verification",
    description: "Extracts and grounds claims with evidence spans",
  },
  {
    id: "comparative",
    label: "Comparative",
    description: "Clusters findings and detects contradictions",
  },
  {
    id: "gap",
    label: "Gap Detection",
    description: "Identifies unexplored research opportunities",
  },
  {
    id: "brief",
    label: "Executive Brief",
    description: "Synthesizes a citation-grounded intelligence report",
  },
  {
    id: "knowledge_graph",
    label: "Knowledge Graph",
    description: "Maps papers, claims, and contradiction edges",
  },
  {
    id: "report",
    label: "PDF Report",
    description: "Generates downloadable executive deliverable",
  },
];

export type AgentStepStatus =
  | "pending"
  | "running"
  | "success"
  | "degraded"
  | "failed"
  | "skipped";

export function agentStatusFromLogs(
  agentId: string,
  logs: Array<{ agent_name: string; status?: string; output_data?: Record<string, unknown> }>,
): AgentStepStatus {
  const log = logs.find((entry) => entry.agent_name === agentId);
  if (!log) return "pending";

  const status = (log.status || "").toLowerCase();
  if (status === "success" || status === "ok") return "success";
  if (status === "partial" || status === "degraded") return "degraded";
  if (status === "failed" || status === "error") return "failed";
  if (status === "skipped") return "skipped";
  if (status === "insufficient_evidence" || status === "no_candidates") {
    return "degraded";
  }
  return "success";
}

export function agentErrorMessage(
  agentId: string,
  logs: Array<{
    agent_name: string;
    status?: string;
    output_data?: Record<string, unknown>;
  }>,
): string | null {
  const log = logs.find((entry) => entry.agent_name === agentId);
  if (!log) return null;
  const status = (log.status || "").toLowerCase();
  if (status !== "error" && status !== "failed") return null;

  const output = log.output_data || {};
  if (typeof output.error === "string") return output.error;

  const nested = output.agent_log as { error?: string } | undefined;
  if (nested?.error) return nested.error;

  const errors = output.errors as Array<{ message?: string }> | undefined;
  if (errors?.[0]?.message) return errors[0].message;

  return "Agent execution failed";
}

import type { AnalyzeResponse, ReportJson, SessionData } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

function apiUrl(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const { timeoutMs, ...fetchInit } = init || {};
  const controller = new AbortController();
  const timer =
    timeoutMs != null
      ? setTimeout(() => controller.abort(), timeoutMs)
      : undefined;

  try {
    const response = await fetch(apiUrl(path), {
      ...fetchInit,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(fetchInit.headers || {}),
      },
    });
    if (!response.ok) {
      let detail = await response.text();
      try {
        const parsed = JSON.parse(detail) as { detail?: string | unknown };
        if (typeof parsed.detail === "string") {
          detail = parsed.detail;
        } else if (parsed.detail) {
          detail = JSON.stringify(parsed.detail);
        }
      } catch {
        /* keep raw */
      }
      const label =
        response.status === 404
          ? "API route not found — rebuild Docker API image"
          : response.status >= 500
            ? "Server error"
            : "Request failed";
      throw new Error(`${label}: ${detail || response.status}`);
    }
    return response.json() as Promise<T>;
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error(
        `Request timed out after ${timeoutMs ?? 0}ms — the API may still be processing`,
      );
    }
    if (err instanceof TypeError) {
      throw new Error(
        `Cannot reach API at ${API_BASE}. Start Docker: docker compose -f docker/docker-compose.yml --env-file docker/.env up -d api`,
      );
    }
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export function knowledgeGraphUrl(sessionId: string): string {
  return apiUrl(`/knowledge-graph/${sessionId}`);
}

export function reportPdfUrl(reportId: string): string {
  return apiUrl(`/report/${reportId}`);
}

export async function knowledgeGraphAvailable(
  sessionId: string,
): Promise<boolean> {
  try {
    const response = await fetch(knowledgeGraphUrl(sessionId), {
      method: "GET",
      cache: "no-store",
    });
    const contentType = response.headers.get("content-type") || "";
    return response.ok && contentType.includes("text/html");
  } catch {
    return false;
  }
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(apiUrl("/health"), {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

export interface AnalyzeOptions {
  fast?: boolean;
  mode?: "benchmark" | "fast" | "demo" | "full";
  force_full?: boolean;
  turbo?: boolean;
}

export async function benchmarkAnalyze(query: string): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/benchmark/analyze", {
    method: "POST",
    body: JSON.stringify({ query }),
    timeoutMs: 30000,
  });
}

export interface AnalyzeStartResponse {
  session_id: string;
  status: string;
  poll_url: string;
}

export async function startAnalysis(
  query: string,
  options?: AnalyzeOptions,
): Promise<AnalyzeStartResponse> {
  return request<AnalyzeStartResponse>("/analyze/start", {
    method: "POST",
    body: JSON.stringify({ query, options: { turbo: true, ...options } }),
    timeoutMs: 30000,
  });
}

export async function analyzeQuery(
  query: string,
  options?: AnalyzeOptions,
): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/analyze", {
    method: "POST",
    body: JSON.stringify({ query, options: options || {} }),
    timeoutMs: 900000,
  });
}

export interface PollSessionOptions {
  intervalMs?: number;
  /** Per-request timeout while polling (discovery can take 60s+). */
  requestTimeoutMs?: number;
  /** Stop polling after this many milliseconds. */
  maxWaitMs?: number;
}

export async function pollSessionUntilComplete(
  sessionId: string,
  onUpdate?: (session: SessionData) => void,
  options?: PollSessionOptions,
): Promise<SessionData> {
  const intervalMs = options?.intervalMs ?? 3000;
  const requestTimeoutMs = options?.requestTimeoutMs ?? 120000;
  const maxWaitMs = options?.maxWaitMs ?? 15 * 60 * 1000;
  const started = Date.now();
  let lastSession: SessionData | null = null;

  for (;;) {
    if (Date.now() - started > maxWaitMs) {
      throw new Error(
        "Analysis is still running on the server — open the session URL or try Benchmark (<8s)",
      );
    }

    try {
      const session = await getSession(sessionId, { timeoutMs: requestTimeoutMs });
      lastSession = session;
      onUpdate?.(session);
      if (session.status === "completed" || session.status === "failed") {
        return session;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const stillStarting = Date.now() - started < maxWaitMs;
      if (!stillStarting) {
        throw err;
      }
      if (lastSession) {
        onUpdate?.(lastSession);
      }
      // API can be busy during long discovery/embedding; keep polling.
      if (!message.includes("timed out") && !message.includes("Cannot reach API")) {
        throw err;
      }
    }

    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export interface BenchmarkMetrics {
  accuracy_pct: number;
  citation_precision_pct: number;
  hallucination_reduction_pct: number;
  synaptiq_hallucination_rate_pct: number;
  baseline_hallucination_rate_pct: number;
  p50_latency_ms: number;
  case_count: number;
  targets_met: Record<string, boolean>;
  evaluated_at: string;
  pitch_targets?: Record<string, number>;
}

export async function getBenchmarkMetrics(): Promise<BenchmarkMetrics> {
  return request<BenchmarkMetrics>("/benchmark/metrics", { timeoutMs: 10000 });
}

export async function getObservabilityStatus(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/observability/status", {
    timeoutMs: 10000,
  });
}

export async function getSession(
  sessionId: string,
  options?: { timeoutMs?: number },
): Promise<SessionData> {
  return request<SessionData>(`/session/${sessionId}`, {
    timeoutMs: options?.timeoutMs ?? 30000,
  });
}

export async function getReportJson(reportId: string): Promise<ReportJson> {
  return request<ReportJson>(`/report/${reportId}/json`);
}

export { API_BASE };

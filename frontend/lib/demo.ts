export interface DemoConfig {
  enabled: boolean;
  sessionId: string;
  reportId: string;
  query: string;
  label: string;
}

export function getDemoConfig(): DemoConfig | null {
  const sessionId = process.env.NEXT_PUBLIC_DEMO_SESSION_ID?.trim();
  const reportId = process.env.NEXT_PUBLIC_DEMO_REPORT_ID?.trim();
  if (!sessionId || !reportId) return null;

  return {
    enabled: true,
    sessionId,
    reportId,
    query:
      process.env.NEXT_PUBLIC_DEMO_QUERY?.trim() ||
      "How do retrieval-augmented generation systems reduce hallucination in scientific QA?",
    label: process.env.NEXT_PUBLIC_DEMO_LABEL?.trim() || "Pre-computed demo run",
  };
}

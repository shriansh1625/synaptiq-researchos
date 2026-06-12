export interface TextBlock {
  text: string;
  citations: string[];
}

export interface GapBlock {
  text: string;
  gap_id: string;
}

export interface ExplainabilityCitation {
  citation_id: string;
  claim_id?: string | null;
  gap_id?: string | null;
  paper_id?: string | null;
  title?: string;
  text_span?: string;
  confidence?: number;
  source?: string;
  verdict?: string | null;
  reasoning?: string;
}

export interface ReportRecommendations {
  report_id?: string;
  title?: string;
  key_findings?: TextBlock[];
  comparative_insights?: TextBlock[];
  contradictions?: TextBlock[];
  research_gaps?: GapBlock[];
  future_opportunities?: TextBlock[];
  recommendations?: TextBlock[];
  limitations?: string;
  overall_confidence?: number;
  knowledge_graph_summary?: Record<string, unknown>;
}

export interface ReportJson {
  report_id: string;
  session_id: string;
  summary: string;
  recommendations: ReportRecommendations;
  citations: ExplainabilityCitation[];
  created_at?: string;
  pdf_available: boolean;
}

export interface AgentLog {
  agent_name: string;
  latency?: number | null;
  confidence_score?: number | null;
  status?: string;
  input_data?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  timestamp?: string | null;
}

export interface SessionData {
  session_id: string;
  query: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  paper_count: number;
  verified_claim_count: number;
  contradiction_count: number;
  research_gap_count: number;
  report_id?: string | null;
  overall_confidence?: number | null;
  agent_logs: AgentLog[];
  errors: Array<Record<string, unknown>>;
}

export interface AnalyzeResponse {
  session_id: string;
  status: string;
  report_id?: string | null;
  overall_confidence?: number | null;
  knowledge_graph_url?: string | null;
  report_url?: string | null;
  errors: Array<Record<string, unknown>>;
}

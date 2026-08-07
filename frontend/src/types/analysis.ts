// AI2BI Phase 0 分析领域类型 — 与后端 apps/ai2bi/analysis_contract.py 对齐

export type AnalysisRunStatus =
  | 'completed'
  | 'data_insufficient'
  | 'blocked'
  | 'failed'
  | 'skipped'
  | 'started'
  | 'generating'

export type AnalysisIntentType =
  | 'knowledge'
  | 'data_lookup'
  | 'chart_only'
  | 'analysis'
  | 'topic_analysis'
  | 'prediction'
  | 'unsupported'

// Q2 分析意图快照 — 与后端 apps/ai2bi/analysis_intent.py 对齐
export interface AnalysisIntent {
  intent_type: AnalysisIntentType
  analysis_required: boolean
  chart_required: boolean
  contract_required: boolean
  confidence: number
  reason: string
  signals: string[]
}

export type FactSource = 'sql' | 'backend_calc' | 'model_inferred'

export interface AnalysisFact {
  fact_id: string
  category: string
  label: string
  value?: number | null
  unit?: string | null
  source_type: FactSource
  formula?: string | null
  input_refs: string[]
  row_refs: string[]
  column?: string | null
  display?: string | null
  status: 'verified' | 'data_insufficient'
  reason?: string | null
}

export interface QaFinding {
  code: string
  severity: 'info' | 'warning' | 'block'
  message: string
  fact_ids: string[]
  source_refs: string[]
}

export interface QaSummary {
  sql_facts: number
  backend_facts: number
  model_facts: number
  data_insufficient: number
  sourced_numbers: number
  derived_count: number
  inferred_count: number
  unsourced_count: number
}

export interface QaResult {
  status: 'passed' | 'warning' | 'blocked'
  findings: QaFinding[]
  summary: QaSummary
  renderable: boolean
}

export interface EvidenceRouteInfo {
  agent?: { id?: number; code?: string; name?: string; vertical?: string } | null
  domain?: string | null
  sub_skill?: string | null
  confidence?: number
  is_fallback?: boolean
  capabilities?: string[]
  analysis_templates?: string[]
}

export interface EvidenceDetail {
  found?: boolean
  evidence_id?: number
  record_id?: number
  chat_id?: number
  agent_id?: number | null
  source_record_id?: number | null
  route_info?: EvidenceRouteInfo | null
  sql_text?: string | null
  sql_executed?: boolean
  sql_row_count?: number
  sql_result_summary?: any | null
  sourced_numbers?: any[]
  derived_numbers?: any[]
  model_inferred?: any[]
  analysis_status?: AnalysisRunStatus | null
  analysis_error?: string | null
  analysis_intent?: AnalysisIntent | null
  topic_contract?: TopicContract | null
  topic_plan?: TopicPlan | null
  topic_bp_output?: BpOutput | null
  topic_queries?: TopicQueryResult[]
  analysis_facts?: AnalysisFact[]
  qa_result?: QaResult | null
  analysis_output?: string | null
  result_hash?: string | null
  metric_context?: any[]
  agent_snapshot?: any | null
  model_name?: string | null
  total_tokens?: number | null
  duration_ms?: number | null
  qa_passed?: boolean | null
  qa_violations?: string[]
  created_at?: string | null
  updated_at?: string | null
}

// SSE 事件负载
export interface AnalysisStatusEvent {
  type: 'analysis_status'
  status: AnalysisRunStatus
  message?: string
}

export interface EvidenceQaEvent {
  type: 'evidence_qa'
  content: string
}

export interface AnalysisEvent {
  type: 'analysis'
  content: string
}

export interface EvidenceReadyEvent {
  type: 'evidence_ready'
  record_id: number
  status?: string
}

export interface AnalysisErrorEvent {
  type: 'analysis_error'
  code: string
  message: string
  retryable?: boolean
}

export type ChatSseEvent =
  | AnalysisStatusEvent
  | EvidenceQaEvent
  | AnalysisEvent
  | EvidenceReadyEvent
  | AnalysisErrorEvent
  | { type: string; [k: string]: any }

// ── Q3 专题分析类型 ──────────────────────────────

export interface TopicContract {
  question: string
  intent_type: string
  agent_ref?: string | null
  topic_template?: string | null
  metrics: string[]
  time_range?: Record<string, any>
  population?: string | null
  dimensions: string[]
  mandatory_filters: string[]
  comparison_baseline?: string | null
  status: string
}

export interface TopicQueryResult {
  query_id: string
  purpose: string
  required: boolean
  status: string
  sql?: string | null
  row_count?: number
  result_hash?: string | null
  error?: string | null
}

export interface TopicPlan {
  plan_id: string
  mode: string
  max_queries: number
  queries: TopicQueryResult[]
  operators: string[]
  limits: Record<string, any>
}

export interface BpFinding {
  category: string
  text: string
  fact_ids: string[]
  query_ids: string[]
}

export interface BpOutput {
  executive_summary: BpFinding[]
  findings: BpFinding[]
  limitations: string[]
  next_questions: string[]
  markdown?: string | null
}
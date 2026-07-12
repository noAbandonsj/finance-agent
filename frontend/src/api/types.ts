export interface ConfigStatus {
  model_configured: boolean
  default_model: string
  deep_model: string
  market_provider: string
}

export interface HealthStatus {
  status: string
  service: string
}

export type ResearchPhase =
  | 'IDLE'
  | 'CREATING'
  | 'RUNNING'
  | 'COMPLETE'
  | 'FAILED'

export interface ResearchRunAccepted {
  run_id: string
  event_url: string
}

export interface ResearchEvent {
  id: string
  run_id: string
  sequence: number
  event_type: string
  message: string
  payload: Record<string, unknown> | null
  terminal: boolean
  created_at: string
}

export interface ToolCallRecord {
  id: string
  run_id: string
  tool_name: string
  arguments: Record<string, unknown>
  result: Record<string, unknown> | null
  provider: string | null
  market_time: string | null
  retrieved_at: string
  duration_ms: number
  success: boolean
  error_code: string | null
}

export interface ResearchRunDetail {
  id: string
  thread_id?: string
  user_query?: string
  symbol: string
  status: string
  model_name?: string
  prompt_version?: string
  started_at?: string
  finished_at?: string | null
  data_cutoff?: string | null
  error_code?: string | null
  error_message?: string | null
  result: { id: string; run_id: string; report_markdown: string; created_at: string } | null
  events: ResearchEvent[]
  tool_calls: ToolCallRecord[]
}

export interface MarketSnapshot {
  symbol: string
  name: string
  security_type: 'STOCK' | 'ETF'
  last: number
  previous_close: number | null
  open: number | null
  high: number | null
  low: number | null
  change_percent: number | null
  volume: number | null
  amount: number | null
  market_time: string
  timestamp_origin: string
  provider: string
  retrieved_at: string
}

export interface DailyBar {
  symbol: string
  trading_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number | null
  provider: string
}

export interface MarketMetrics {
  symbol: string
  observation_count: number
  start_date: string
  end_date: string
  returns: Record<string, number | null>
  moving_averages: Record<string, number | null>
  annualized_volatility: number | null
  max_drawdown: number | null
  volume_ratio: number | null
}

export interface WatchlistItem {
  symbol: string
  display_name: string
  security_type: 'STOCK' | 'ETF'
  note: string | null
  created_at: string
}

export interface ResearchRunSummary {
  id: string
  user_query: string
  symbol: string
  status: string
  model_name: string
  started_at: string
  finished_at?: string | null
}

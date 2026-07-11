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

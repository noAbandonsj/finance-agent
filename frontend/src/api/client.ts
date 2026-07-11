import axios from 'axios'

import type {
  ConfigStatus,
  DailyBar,
  HealthStatus,
  MarketSnapshot,
  ResearchRunAccepted,
  ResearchRunDetail,
} from './types'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 25_000,
})

export async function getHealth(): Promise<HealthStatus> {
  const response = await apiClient.get<HealthStatus>('/health')
  return response.data
}

export async function getConfigStatus(): Promise<ConfigStatus> {
  const response = await apiClient.get<ConfigStatus>('/config/status')
  return response.data
}

export async function createResearchRun(
  symbol: string,
  question: string,
): Promise<ResearchRunAccepted> {
  const response = await apiClient.post<ResearchRunAccepted>('/research/runs', { symbol, question })
  return response.data
}

export async function getResearchRun(runId: string): Promise<ResearchRunDetail> {
  const response = await apiClient.get<ResearchRunDetail>(`/research/runs/${runId}`)
  return response.data
}

export async function getMarketSnapshot(symbol: string): Promise<MarketSnapshot> {
  const response = await apiClient.get<MarketSnapshot>(`/market/${symbol}/snapshot`)
  return response.data
}

export async function getDailyBars(symbol: string, tradingDays = 120): Promise<DailyBar[]> {
  const response = await apiClient.get<DailyBar[]>(`/market/${symbol}/daily-bars`, {
    params: { trading_days: tradingDays },
  })
  return response.data
}

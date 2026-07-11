import axios from 'axios'

import type { ConfigStatus, HealthStatus } from './types'

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

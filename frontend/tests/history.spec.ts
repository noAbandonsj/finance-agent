import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import * as api from '../src/api/client'
import { useHistoryStore } from '../src/stores/history'

beforeEach(() => setActivePinia(createPinia()))

it('loads filtered history and restores a selected result', async () => {
  vi.spyOn(api, 'getResearchRuns').mockResolvedValue([
    {
      id: 'run-1',
      symbol: '600519.SH',
      status: 'COMPLETE',
      model_name: 'deepseek-v4-pro',
      started_at: '2026-07-11T00:00:00Z',
      market_view: 'NEUTRAL',
      confidence: 0.6,
      horizon: '20 trading days',
      summary: 'Balanced',
    },
  ])
  vi.spyOn(api, 'getResearchRun').mockResolvedValue({
    id: 'run-1',
    symbol: '600519.SH',
    status: 'COMPLETE',
    result: { full_result: { summary: 'Balanced' } },
    events: [],
    tool_calls: [],
  } as never)

  const store = useHistoryStore()
  store.statusFilter = 'COMPLETE'
  await store.load()
  await store.select('run-1')

  expect(store.filteredRuns).toHaveLength(1)
  expect(store.selected?.result?.full_result.summary).toBe('Balanced')
})

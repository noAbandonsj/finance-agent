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
      user_query: '分析当前状态',
      started_at: '2026-07-11T00:00:00Z',
    },
  ])
  vi.spyOn(api, 'getResearchRun').mockResolvedValue({
    id: 'run-1',
    symbol: '600519.SH',
    status: 'COMPLETE',
    result: {
      id: 'result-1',
      run_id: 'run-1',
      report_markdown: '# Report\n\nBalanced',
      created_at: '2026-07-11T00:01:00Z',
    },
    events: [],
    tool_calls: [],
  } as never)

  const store = useHistoryStore()
  store.statusFilter = 'COMPLETE'
  await store.load()
  await store.select('run-1')

  expect(store.filteredRuns).toHaveLength(1)
  expect(store.selected?.result?.report_markdown).toContain('Balanced')
})

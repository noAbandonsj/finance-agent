import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import * as api from '../src/api/client'
import { useResearchStore } from '../src/stores/research'

class FakeEventSource {
  static latest: FakeEventSource | null = null
  readonly listeners = new Map<string, (event: MessageEvent) => void>()
  closed = false

  constructor(readonly url: string) {
    FakeEventSource.latest = this
  }

  addEventListener(type: string, listener: EventListener): void {
    this.listeners.set(type, listener as (event: MessageEvent) => void)
  }

  close(): void {
    this.closed = true
  }

  emit(type: string, payload: object = {}): void {
    this.listeners.get(type)?.(
      new MessageEvent(type, {
        data: JSON.stringify({ message: type, payload }),
        lastEventId: '4',
      }),
    )
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.stubGlobal('EventSource', FakeEventSource)
  FakeEventSource.latest = null
})

it('creates a run, streams completion, and restores market data', async () => {
  vi.spyOn(api, 'createResearchRun').mockResolvedValue({
    run_id: 'run-1',
    event_url: '/api/research/runs/run-1/events',
  })
  vi.spyOn(api, 'getResearchRun').mockResolvedValue({
    id: 'run-1',
    status: 'COMPLETE',
    symbol: '600519.SH',
    result: {
      id: 'result-1',
      run_id: 'run-1',
      report_markdown: '# Report\n\nBalanced',
      created_at: '2026-07-11T00:00:00Z',
    },
    events: [],
    tool_calls: [
      {
        id: 'snapshot-1',
        run_id: 'run-1',
        tool_name: 'get_market_snapshot',
        arguments: { symbol: '600519.SH' },
        result: { symbol: '600519.SH', last: 1400 },
        provider: 'test',
        market_time: '2026-07-11T00:00:00Z',
        retrieved_at: '2026-07-11T00:00:01Z',
        duration_ms: 1,
        success: true,
        error_code: null,
      },
      {
        id: 'history-1',
        run_id: 'run-1',
        tool_name: 'get_price_history',
        arguments: { symbol: '600519.SH' },
        result: {
          bars: [{ symbol: '600519.SH', trading_date: '2026-07-10', close: 1400 }],
        },
        provider: 'test',
        market_time: '2026-07-10T00:00:00Z',
        retrieved_at: '2026-07-11T00:00:01Z',
        duration_ms: 1,
        success: true,
        error_code: null,
      },
    ],
  } as never)
  const snapshotSpy = vi.spyOn(api, 'getMarketSnapshot')
  const barsSpy = vi.spyOn(api, 'getDailyBars')

  const store = useResearchStore()
  await store.submit('600519', '分析当前状态')

  expect(store.phase).toBe('RUNNING')
  expect(FakeEventSource.latest?.url).toBe('/api/research/runs/run-1/events')

  FakeEventSource.latest?.emit('RUN_COMPLETED')
  await vi.waitFor(() => expect(store.phase).toBe('COMPLETE'))

  expect(store.snapshot?.symbol).toBe('600519.SH')
  expect(store.bars).toHaveLength(1)
  expect(store.report).toContain('Balanced')
  expect(snapshotSpy).not.toHaveBeenCalled()
  expect(barsSpy).not.toHaveBeenCalled()
  expect(FakeEventSource.latest?.closed).toBe(true)
})

it('closes the previous stream before another submission', async () => {
  vi.spyOn(api, 'createResearchRun')
    .mockResolvedValueOnce({ run_id: 'run-1', event_url: '/events/1' })
    .mockResolvedValueOnce({ run_id: 'run-2', event_url: '/events/2' })

  const store = useResearchStore()
  await store.submit('600519', 'first question')
  const first = FakeEventSource.latest
  await store.submit('510300', 'second question')

  expect(first?.closed).toBe(true)
  expect(store.activeRunId).toBe('run-2')
})

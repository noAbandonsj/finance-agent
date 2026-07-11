import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import * as api from '../src/api/client'
import { useWatchlistStore } from '../src/stores/watchlist'

beforeEach(() => setActivePinia(createPinia()))

it('loads, adds, and removes canonical watchlist symbols', async () => {
  vi.spyOn(api, 'getWatchlist').mockResolvedValue([])
  vi.spyOn(api, 'addWatchlistItem').mockResolvedValue({
    symbol: '600519.SH',
    display_name: '贵州茅台',
    security_type: 'STOCK',
    note: null,
    created_at: '2026-07-11T00:00:00Z',
  })
  vi.spyOn(api, 'getMarketSnapshot').mockResolvedValue({
    symbol: '600519.SH',
    last: 1400,
    market_time: '2026-07-11T00:00:00Z',
  } as never)
  vi.spyOn(api, 'removeWatchlistItem').mockResolvedValue()

  const store = useWatchlistStore()
  await store.load()
  await store.add('600519')
  expect(store.items).toHaveLength(1)
  expect(store.items[0].symbol).toBe('600519.SH')
  expect(store.items[0].snapshot?.last).toBe(1400)

  await store.remove('600519.SH')
  expect(store.items).toEqual([])
})

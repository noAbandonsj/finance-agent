import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  addWatchlistItem,
  getMarketSnapshot,
  getWatchlist,
  removeWatchlistItem,
} from '@/api/client'
import type { MarketSnapshot, WatchlistItem } from '@/api/types'

export interface WatchlistRow extends WatchlistItem {
  snapshot: MarketSnapshot | null
}

export const useWatchlistStore = defineStore('watchlist', () => {
  const items = ref<WatchlistRow[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function attachSnapshot(item: WatchlistItem): Promise<WatchlistRow> {
    try {
      return { ...item, snapshot: await getMarketSnapshot(item.symbol) }
    } catch {
      return { ...item, snapshot: null }
    }
  }

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      items.value = await Promise.all((await getWatchlist()).map(attachSnapshot))
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '无法加载自选列表'
    } finally {
      loading.value = false
    }
  }

  async function add(symbol: string, note?: string): Promise<void> {
    const saved = await addWatchlistItem(symbol, note)
    const row = await attachSnapshot(saved)
    const existing = items.value.findIndex((item) => item.symbol === saved.symbol)
    if (existing >= 0) items.value.splice(existing, 1, row)
    else items.value.push(row)
  }

  async function remove(symbol: string): Promise<void> {
    await removeWatchlistItem(symbol)
    items.value = items.value.filter((item) => item.symbol !== symbol)
  }

  return { items, loading, error, load, add, remove }
})

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { getResearchRun, getResearchRuns } from '@/api/client'
import type { ResearchRunDetail, ResearchRunSummary } from '@/api/types'

export const useHistoryStore = defineStore('history', () => {
  const runs = ref<ResearchRunSummary[]>([])
  const selected = ref<ResearchRunDetail | null>(null)
  const statusFilter = ref('ALL')
  const loading = ref(false)
  const error = ref<string | null>(null)

  const filteredRuns = computed(() =>
    runs.value.filter((run) => statusFilter.value === 'ALL' || run.status === statusFilter.value),
  )

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      runs.value = await getResearchRuns()
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '无法加载研究历史'
    } finally {
      loading.value = false
    }
  }

  async function select(runId: string): Promise<void> {
    selected.value = await getResearchRun(runId)
  }

  return {
    runs,
    selected,
    statusFilter,
    loading,
    error,
    filteredRuns,
    load,
    select,
  }
})

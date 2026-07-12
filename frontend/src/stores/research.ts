import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import {
  createResearchRun,
  getResearchRun,
} from '@/api/client'
import type {
  DailyBar,
  MarketMetrics,
  MarketSnapshot,
  ResearchEvent,
  ResearchPhase,
  ResearchRunDetail,
} from '@/api/types'

const progressEvents = ['RUN_CREATED', 'AGENT_STARTED', 'AGENT_COMPLETED'] as const
const terminalEvents = ['RUN_COMPLETED', 'RUN_FAILED'] as const

export const useResearchStore = defineStore('research', () => {
  const phase = ref<ResearchPhase>('IDLE')
  const activeRunId = ref<string | null>(null)
  const events = ref<Array<Pick<ResearchEvent, 'event_type' | 'message' | 'payload'>>>([])
  const detail = ref<ResearchRunDetail | null>(null)
  const snapshot = ref<MarketSnapshot | null>(null)
  const bars = ref<DailyBar[]>([])
  const metrics = ref<MarketMetrics | null>(null)
  const error = ref<string | null>(null)
  let eventSource: EventSource | null = null

  const report = computed(() => detail.value?.result?.report_markdown ?? null)
  const running = computed(() => phase.value === 'CREATING' || phase.value === 'RUNNING')

  async function submit(symbol: string, question: string): Promise<void> {
    closeStream()
    phase.value = 'CREATING'
    activeRunId.value = null
    events.value = []
    detail.value = null
    snapshot.value = null
    bars.value = []
    metrics.value = null
    error.value = null

    try {
      const accepted = await createResearchRun(symbol, question)
      activeRunId.value = accepted.run_id
      phase.value = 'RUNNING'
      openStream(accepted.event_url)
    } catch (cause) {
      phase.value = 'FAILED'
      error.value = cause instanceof Error ? cause.message : '无法创建研究任务'
    }
  }

  function appendEvent(type: string, rawEvent: Event): void {
    const event = rawEvent as MessageEvent<string>
    const data = JSON.parse(event.data) as {
      message: string
      payload?: Record<string, unknown>
    }
    events.value.push({
      event_type: type,
      message: data.message,
      payload: data.payload ?? null,
    })
  }

  function openStream(url: string): void {
    eventSource = new EventSource(url)
    for (const type of [...progressEvents, 'TOOL_STARTED', 'TOOL_COMPLETED', 'TOOL_FAILED']) {
      eventSource.addEventListener(type, (event) => appendEvent(type, event))
    }
    for (const type of terminalEvents) {
      eventSource.addEventListener(type, (rawEvent) => {
        appendEvent(type, rawEvent)
        void finalize()
      })
    }
    eventSource.onerror = () => {
      if (running.value) error.value = '研究进度连接中断，可稍后从历史记录恢复'
    }
  }

  async function finalize(): Promise<void> {
    const runId = activeRunId.value
    if (!runId) return
    closeStream()
    try {
      const runDetail = await getResearchRun(runId)
      detail.value = runDetail
      if (runDetail.status === 'FAILED') {
        phase.value = 'FAILED'
        error.value = runDetail.error_message || '研究任务失败'
        return
      }
      const snapshotCall = [...runDetail.tool_calls]
        .reverse()
        .find((call) => call.tool_name === 'get_market_snapshot' && call.success)
      snapshot.value = (snapshotCall?.result as unknown as MarketSnapshot) ?? null
      const historyCall = [...runDetail.tool_calls]
        .reverse()
        .find((call) => call.tool_name === 'get_price_history' && call.success)
      const historyResult = historyCall?.result as { bars?: DailyBar[] } | null | undefined
      bars.value = historyResult?.bars ?? []
      const metricsCall = runDetail.tool_calls.find(
        (call) => call.tool_name === 'calculate_market_metrics' && call.success,
      )
      metrics.value = (metricsCall?.result as unknown as MarketMetrics) ?? null
      phase.value = 'COMPLETE'
    } catch (cause) {
      phase.value = 'FAILED'
      error.value = cause instanceof Error ? cause.message : '无法加载研究结果'
    }
  }

  async function restore(runId: string): Promise<void> {
    activeRunId.value = runId
    await finalize()
  }

  function closeStream(): void {
    eventSource?.close()
    eventSource = null
  }

  function dispose(): void {
    closeStream()
  }

  return {
    phase,
    activeRunId,
    events,
    detail,
    snapshot,
    bars,
    metrics,
    error,
    report,
    running,
    submit,
    restore,
    dispose,
  }
})

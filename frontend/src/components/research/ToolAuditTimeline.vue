<script setup lang="ts">
import { computed } from 'vue'

import type { ResearchEvent, ResearchPhase, ToolCallRecord } from '@/api/types'

const props = defineProps<{
  phase: ResearchPhase
  events: Array<Pick<ResearchEvent, 'event_type' | 'message' | 'payload'>>
  toolCalls: ToolCallRecord[]
}>()

const liveToolEvents = computed(() =>
  props.events.filter((event) => event.event_type.startsWith('TOOL_')),
)
const settled = computed(() => ['COMPLETE', 'FAILED'].includes(props.phase))

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2)
}
</script>

<template>
  <section class="tool-audit">
    <div class="section-label"><span>工具审计</span></div>

    <div v-if="phase === 'RUNNING' && liveToolEvents.length" class="tool-live-events">
      <div v-for="(event, index) in liveToolEvents" :key="`${event.event_type}-${index}`">
        <span :class="{ 'is-error': event.event_type === 'TOOL_FAILED' }">
          {{ event.message }}
        </span>
      </div>
    </div>

    <el-collapse v-if="toolCalls.length" class="tool-call-list">
      <el-collapse-item v-for="call in toolCalls" :key="call.id" :name="call.id">
        <template #title>
          <span class="tool-call-title" :class="{ 'is-error': !call.success }">
            {{ call.tool_name }} · {{ call.success ? '完成' : '失败' }} · {{ call.duration_ms }}ms
          </span>
        </template>
        <dl class="tool-call-meta">
          <dt>证据 ID</dt><dd><code>{{ call.id }}</code></dd>
          <dt>数据来源</dt><dd>{{ call.provider ?? '-' }}</dd>
          <dt>市场时间</dt><dd>{{ call.market_time ? new Date(call.market_time).toLocaleString('zh-CN') : '-' }}</dd>
          <dt>错误码</dt><dd>{{ call.error_code ?? '-' }}</dd>
        </dl>
        <h4>参数</h4>
        <pre>{{ formatJson(call.arguments) }}</pre>
        <h4>结果</h4>
        <pre>{{ formatJson(call.result) }}</pre>
      </el-collapse-item>
    </el-collapse>

    <p v-else-if="settled" class="tool-audit-empty">本次报告未使用外部行情工具</p>
    <p v-else class="tool-audit-empty">等待 Agent 选择工具</p>
  </section>
</template>

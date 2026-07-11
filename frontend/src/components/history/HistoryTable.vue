<script setup lang="ts">
import type { ResearchRunSummary } from '@/api/types'

defineProps<{ rows: ResearchRunSummary[]; loading: boolean }>()
const emit = defineEmits<{ select: [runId: string] }>()

function formatTime(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}
</script>

<template>
  <el-table
    :data="rows"
    :loading="loading"
    row-key="id"
    class="history-table"
    @row-click="(row: ResearchRunSummary) => emit('select', row.id)"
  >
    <el-table-column label="时间" min-width="150">
      <template #default="scope">{{ formatTime(scope.row.started_at) }}</template>
    </el-table-column>
    <el-table-column prop="symbol" label="标的" min-width="110" />
    <el-table-column prop="status" label="状态" min-width="100" />
    <el-table-column prop="market_view" label="观点" min-width="90" />
    <el-table-column label="置信度" min-width="90">
      <template #default="scope">
        {{ scope.row.confidence == null ? '-' : `${Math.round(scope.row.confidence * 100)}%` }}
      </template>
    </el-table-column>
    <el-table-column prop="horizon" label="周期" min-width="130" />
    <el-table-column prop="model_name" label="模型" min-width="160" show-overflow-tooltip />
  </el-table>
</template>

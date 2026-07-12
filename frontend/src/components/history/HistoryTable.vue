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
    <el-table-column prop="user_query" label="研究问题" min-width="220" show-overflow-tooltip />
    <el-table-column prop="model_name" label="模型" min-width="160" show-overflow-tooltip />
  </el-table>
</template>

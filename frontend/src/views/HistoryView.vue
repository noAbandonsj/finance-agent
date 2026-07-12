<script setup lang="ts">
import { onMounted } from 'vue'

import HistoryTable from '@/components/history/HistoryTable.vue'
import ResearchReport from '@/components/research/ResearchReport.vue'
import ToolAuditTimeline from '@/components/research/ToolAuditTimeline.vue'
import { useHistoryStore } from '@/stores/history'

const history = useHistoryStore()
onMounted(() => history.load())
</script>

<template>
  <section class="page-section">
    <div class="page-heading">
      <div>
        <p class="eyebrow">DECISION LOG</p>
        <h1>研究历史</h1>
      </div>
    </div>

    <div class="history-filters">
      <el-select v-model="history.statusFilter" aria-label="状态筛选">
        <el-option label="全部状态" value="ALL" />
        <el-option label="完成" value="COMPLETE" />
        <el-option label="失败" value="FAILED" />
      </el-select>
    </div>

    <div class="history-layout">
      <HistoryTable :rows="history.filteredRuns" :loading="history.loading" @select="history.select" />
      <div v-if="history.selected?.result" class="history-result">
        <ResearchReport :markdown="history.selected.result.report_markdown" />
        <ToolAuditTimeline
          phase="COMPLETE"
          :events="history.selected.events"
          :tool-calls="history.selected.tool_calls"
        />
      </div>
      <div v-else class="history-empty">选择一条记录查看完整结果</div>
    </div>
  </section>
</template>

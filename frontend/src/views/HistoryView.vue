<script setup lang="ts">
import { onMounted } from 'vue'

import AnalysisResult from '@/components/research/AnalysisResult.vue'
import HistoryTable from '@/components/history/HistoryTable.vue'
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
      <el-select v-model="history.viewFilter" aria-label="观点筛选">
        <el-option label="全部观点" value="ALL" />
        <el-option label="偏多" value="BULLISH" />
        <el-option label="中性" value="NEUTRAL" />
        <el-option label="偏空" value="BEARISH" />
        <el-option label="不确定" value="UNCERTAIN" />
      </el-select>
    </div>

    <div class="history-layout">
      <HistoryTable :rows="history.filteredRuns" :loading="history.loading" @select="history.select" />
      <AnalysisResult
        v-if="history.selected?.result"
        :analysis="history.selected.result.full_result"
      />
      <div v-else class="history-empty">选择一条记录查看完整结果</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount } from 'vue'

import AnalysisResult from '@/components/research/AnalysisResult.vue'
import MetricsStrip from '@/components/research/MetricsStrip.vue'
import PriceChart from '@/components/research/PriceChart.vue'
import ResearchForm from '@/components/research/ResearchForm.vue'
import ResearchProgress from '@/components/research/ResearchProgress.vue'
import { useResearchStore } from '@/stores/research'

const research = useResearchStore()

onBeforeUnmount(() => research.dispose())
</script>

<template>
  <section class="page-section">
    <div class="page-heading">
      <div>
        <p class="eyebrow">AI RESEARCH</p>
        <h1>金融研究</h1>
      </div>
    </div>

    <div class="research-workspace">
      <section class="research-market-pane">
        <ResearchForm :running="research.running" @submit="research.submit" />
        <ResearchProgress :phase="research.phase" :events="research.events" />
        <MetricsStrip :snapshot="research.snapshot" :metrics="research.metrics" />
        <div class="chart-band">
          <div class="section-label">
            <span>价格与成交量</span>
            <span v-if="research.snapshot">{{ research.snapshot.symbol }}</span>
          </div>
          <PriceChart :bars="research.bars" />
        </div>
      </section>

      <section class="research-analysis-pane">
        <AnalysisResult v-if="research.analysis" :analysis="research.analysis" />
        <div v-else class="analysis-empty">
          <span>等待研究任务</span>
        </div>
        <el-alert
          v-if="research.error"
          class="research-error"
          type="error"
          :title="research.error"
          :closable="false"
          show-icon
        />
      </section>
    </div>
  </section>
</template>

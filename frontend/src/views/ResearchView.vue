<script setup lang="ts">
import { computed, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

import MetricsStrip from '@/components/research/MetricsStrip.vue'
import PriceChart from '@/components/research/PriceChart.vue'
import ResearchForm from '@/components/research/ResearchForm.vue'
import ResearchProgress from '@/components/research/ResearchProgress.vue'
import ResearchReport from '@/components/research/ResearchReport.vue'
import ToolAuditTimeline from '@/components/research/ToolAuditTimeline.vue'
import { useResearchStore } from '@/stores/research'
import { useSystemStore } from '@/stores/system'

const research = useResearchStore()
const system = useSystemStore()
const route = useRoute()
const initialSymbol = computed(() =>
  typeof route.query.symbol === 'string' ? route.query.symbol : '600519',
)

const stamp = new Date()
const pad = (value: number) => String(value).padStart(2, '0')
const briefNo = `${stamp.getFullYear()}-${pad(stamp.getMonth() + 1)}${pad(stamp.getDate())}`
const briefTime = `${pad(stamp.getHours())}:${pad(stamp.getMinutes())}`

onBeforeUnmount(() => research.dispose())
</script>

<template>
  <section class="page-section">
    <div class="brief-masthead">
      <span class="brief-no">Brief №{{ briefNo }}</span>
      <span class="brief-sep" />
      <span class="brief-time">{{ briefTime }}</span>
      <span class="brief-sep" />
      <span>AI 研究工作台</span>
      <span class="brief-state" :class="{ 'is-online': system.backendConnected }">
        {{ system.backendConnected ? '本机服务在线' : '本机服务离线' }}
      </span>
    </div>

    <div class="page-heading">
      <div>
        <p class="eyebrow">AI RESEARCH</p>
        <h1>金融研究</h1>
      </div>
    </div>

    <div class="research-workspace">
      <section class="research-market-pane">
        <ResearchForm
          :running="research.running"
          :initial-symbol="initialSymbol"
          @submit="research.submit"
        />
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
        <ResearchReport v-if="research.report" :markdown="research.report" />
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
        <ToolAuditTimeline
          :phase="research.phase"
          :events="research.events"
          :tool-calls="research.detail?.tool_calls ?? []"
        />
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { ResearchAnalysis } from '@/api/types'

const props = defineProps<{ analysis: ResearchAnalysis }>()

const directionalClass = computed(() => {
  if (props.analysis.status !== 'COMPLETE') return ''
  if (props.analysis.market_view === 'BULLISH') return 'is-bullish'
  if (props.analysis.market_view === 'BEARISH') return 'is-bearish'
  return ''
})

const viewLabel = computed(() => {
  const labels = {
    BULLISH: '偏多',
    NEUTRAL: '中性',
    BEARISH: '偏空',
    UNCERTAIN: '不确定',
  }
  return labels[props.analysis.market_view]
})

const needleLeft = computed(() => {
  const confidence = props.analysis.confidence
  const view = props.analysis.market_view
  if (view === 'BULLISH') return `${50 + confidence * 50}%`
  if (view === 'BEARISH') return `${50 - confidence * 50}%`
  return '50%'
})
</script>

<template>
  <article class="analysis-result" :class="directionalClass">
    <header class="analysis-header">
      <div>
        <span class="view-label" :class="directionalClass">{{ viewLabel }}</span>
        <h2>{{ analysis.security_name }} · {{ analysis.symbol }}</h2>
      </div>
      <div class="view-gauge">
        <div class="view-gauge-value">
          <span>置信度</span>
          <strong>{{ Math.round(analysis.confidence * 100) }}%</strong>
        </div>
        <div class="view-gauge-track">
          <span class="view-gauge-needle" :style="{ left: needleLeft }" />
        </div>
        <div class="view-gauge-scale"><span>偏空</span><span>偏多</span></div>
      </div>
    </header>

    <p class="analysis-summary">{{ analysis.summary }}</p>

    <section v-if="analysis.supporting_evidence.length" class="evidence-section">
      <h3>支持证据</h3>
      <div v-for="item in analysis.supporting_evidence" :key="item.evidence_id" class="evidence-row">
        <code>{{ item.evidence_id.slice(0, 8) }}</code>
        <p data-testid="evidence-statement" class="evidence-statement">{{ item.statement }}</p>
      </div>
    </section>

    <section v-if="analysis.opposing_evidence.length" class="evidence-section opposing">
      <h3>反对证据</h3>
      <div v-for="item in analysis.opposing_evidence" :key="item.evidence_id" class="evidence-row">
        <code>{{ item.evidence_id.slice(0, 8) }}</code>
        <p data-testid="evidence-statement" class="evidence-statement">{{ item.statement }}</p>
      </div>
    </section>

    <div class="analysis-lists">
      <section>
        <h3>主要风险</h3>
        <ul><li v-for="risk in analysis.risks" :key="risk">{{ risk }}</li></ul>
      </section>
      <section>
        <h3>失效条件</h3>
        <ul><li v-for="condition in analysis.invalidation_conditions" :key="condition">{{ condition }}</li></ul>
      </section>
    </div>

    <footer class="analysis-meta">
      <span>周期 {{ analysis.horizon }}</span>
      <span>数据截止 {{ new Date(analysis.data_cutoff).toLocaleString('zh-CN') }}</span>
      <span>{{ analysis.model_name }}</span>
    </footer>
  </article>
</template>

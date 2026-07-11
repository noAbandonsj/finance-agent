<script setup lang="ts">
import type { MarketMetrics, MarketSnapshot } from '@/api/types'

defineProps<{ snapshot: MarketSnapshot | null; metrics: MarketMetrics | null }>()

function percent(value: number | null | undefined): string {
  return value == null ? '-' : `${(value * 100).toFixed(2)}%`
}

function price(value: number | null | undefined): string {
  return value == null ? '-' : `¥${value.toLocaleString('zh-CN', { maximumFractionDigits: 3 })}`
}

function returnClass(value: number | null | undefined): string {
  if (value == null) return ''
  return value >= 0 ? 'is-up' : 'is-down'
}
</script>

<template>
  <div class="metrics-strip">
    <div><span>最新</span><strong>{{ price(snapshot?.last) }}</strong></div>
    <div>
      <span>5日收益</span>
      <strong :class="returnClass(metrics?.returns['5d'])">{{ percent(metrics?.returns['5d']) }}</strong>
    </div>
    <div>
      <span>20日收益</span>
      <strong :class="returnClass(metrics?.returns['20d'])">{{ percent(metrics?.returns['20d']) }}</strong>
    </div>
    <div><span>年化波动</span><strong>{{ percent(metrics?.annualized_volatility) }}</strong></div>
    <div>
      <span>最大回撤</span>
      <strong :class="returnClass(metrics?.max_drawdown)">{{ percent(metrics?.max_drawdown) }}</strong>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BarChart, LineChart } from 'echarts/charts'
import { DataZoomComponent, GridComponent, TooltipComponent } from 'echarts/components'
import { init, use, type ECharts } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { DailyBar } from '@/api/types'

use([LineChart, BarChart, GridComponent, TooltipComponent, DataZoomComponent, CanvasRenderer])

const props = defineProps<{ bars: DailyBar[] }>()
const chartElement = ref<HTMLDivElement | null>(null)
let chart: ECharts | null = null

function render(): void {
  if (!chart) return
  chart.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    grid: [
      { left: 54, right: 18, top: 18, height: '61%' },
      { left: 54, right: 18, top: '75%', height: '15%' },
    ],
    xAxis: [
      { type: 'category', data: props.bars.map((bar) => bar.trading_date), boundaryGap: false },
      {
        type: 'category',
        gridIndex: 1,
        data: props.bars.map((bar) => bar.trading_date),
        axisLabel: { show: false },
      },
    ],
    yAxis: [
      { type: 'value', scale: true, splitLine: { lineStyle: { color: '#e2e5e1' } } },
      { type: 'value', gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } },
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1], start: 25, end: 100 }],
    series: [
      {
        name: '收盘价',
        type: 'line',
        data: props.bars.map((bar) => bar.close),
        showSymbol: false,
        lineStyle: { width: 2, color: '#2c5c7c' },
        areaStyle: { color: 'rgba(44, 92, 124, 0.08)' },
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: props.bars.map((bar) => bar.volume),
        itemStyle: { color: '#aeb8b3' },
      },
    ],
  })
}

function resize(): void {
  chart?.resize()
}

onMounted(() => {
  if (!chartElement.value) return
  chart = init(chartElement.value)
  render()
  window.addEventListener('resize', resize)
})

watch(
  () => props.bars,
  async () => {
    await nextTick()
    render()
  },
  { deep: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})
</script>

<template>
  <div ref="chartElement" class="price-chart" role="img" aria-label="价格与成交量图表" />
</template>

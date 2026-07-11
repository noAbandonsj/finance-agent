<script setup lang="ts">
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'

defineProps<{ running: boolean }>()
const emit = defineEmits<{ submit: [symbol: string, question: string] }>()

const symbol = ref('600519')
const question = ref('结合最新行情和量价指标，分析当前状态、主要风险与失效条件。')

function submit(): void {
  const normalizedSymbol = symbol.value.trim()
  const normalizedQuestion = question.value.trim()
  if (!normalizedSymbol || normalizedQuestion.length < 2) return
  emit('submit', normalizedSymbol, normalizedQuestion)
}
</script>

<template>
  <form class="research-form" @submit.prevent="submit">
    <el-input v-model="symbol" class="symbol-input" placeholder="证券代码，如 600519" clearable />
    <el-input
      v-model="question"
      class="question-input"
      type="textarea"
      :rows="3"
      resize="none"
      maxlength="2000"
      show-word-limit
      placeholder="输入研究问题"
    />
    <el-button
      class="research-submit"
      type="primary"
      native-type="submit"
      :icon="Search"
      :loading="running"
      :disabled="running"
    >
      开始研究
    </el-button>
  </form>
</template>

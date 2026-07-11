<script setup lang="ts">
defineProps<{
  phase: string
  events: Array<{ event_type: string; message: string }>
}>()
</script>

<template>
  <div v-if="phase !== 'IDLE'" class="research-progress" aria-live="polite">
    <div class="progress-line">
      <span class="progress-pulse" :class="{ settled: !['CREATING', 'RUNNING'].includes(phase) }" />
      <strong>{{ phase === 'RUNNING' ? 'Agent 正在调用金融工具' : phase }}</strong>
    </div>
    <span v-if="events.length" class="progress-message">{{ events.at(-1)?.message }}</span>
  </div>
</template>

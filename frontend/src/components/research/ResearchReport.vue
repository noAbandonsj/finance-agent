<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, ref, watchPostEffect } from 'vue'

const props = defineProps<{ markdown: string }>()
const root = ref<HTMLElement | null>(null)

const rendered = computed(() => {
  const html = marked.parse(props.markdown, { async: false }) as string
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
})

watchPostEffect(() => {
  for (const link of root.value?.querySelectorAll('a') ?? []) {
    link.target = '_blank'
    link.rel = 'noopener noreferrer'
  }
})
</script>

<template>
  <article class="research-report">
    <div ref="root" class="research-report-body" data-testid="research-report" v-html="rendered" />
  </article>
</template>

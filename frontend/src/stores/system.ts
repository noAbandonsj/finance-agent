import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { getConfigStatus, getHealth } from '@/api/client'

export const useSystemStore = defineStore('system', () => {
  const backendConnected = ref(false)
  const modelConfigured = ref(false)
  const defaultModel = ref('')
  const deepModel = ref('')
  const marketProvider = ref('')
  const loading = ref(false)
  const error = ref<string | null>(null)

  const ready = computed(() => backendConnected.value && modelConfigured.value)

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const [health, config] = await Promise.all([getHealth(), getConfigStatus()])
      backendConnected.value = health.status === 'ok'
      modelConfigured.value = config.model_configured
      defaultModel.value = config.default_model
      deepModel.value = config.deep_model
      marketProvider.value = config.market_provider
    } catch (cause) {
      backendConnected.value = false
      error.value = cause instanceof Error ? cause.message : '无法连接后端服务'
    } finally {
      loading.value = false
    }
  }

  return {
    backendConnected,
    modelConfigured,
    defaultModel,
    deepModel,
    marketProvider,
    loading,
    error,
    ready,
    load,
  }
})

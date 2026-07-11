import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import * as api from '../src/api/client'
import { useSystemStore } from '../src/stores/system'

beforeEach(() => {
  setActivePinia(createPinia())
})

it('loads non-secret backend configuration status', async () => {
  vi.spyOn(api, 'getHealth').mockResolvedValue({
    status: 'ok',
    service: 'ai-finance-backend',
  })
  vi.spyOn(api, 'getConfigStatus').mockResolvedValue({
    model_configured: true,
    default_model: 'deepseek-v4-flash',
    deep_model: 'deepseek-v4-pro',
    market_provider: 'akshare',
  })

  const store = useSystemStore()
  await store.load()

  expect(store.modelConfigured).toBe(true)
  expect(store.defaultModel).toBe('deepseek-v4-flash')
  expect(store.error).toBeNull()
})

<script setup lang="ts">
import { onMounted } from 'vue'
import { Clock, DataAnalysis, Setting, Star } from '@element-plus/icons-vue'

import { useSystemStore } from '@/stores/system'

const system = useSystemStore()

const navigation = [
  { to: '/research', label: '研究', icon: DataAnalysis },
  { to: '/watchlist', label: '自选', icon: Star },
  { to: '/history', label: '历史', icon: Clock },
  { to: '/settings', label: '设置', icon: Setting },
]

onMounted(() => system.load())
</script>

<template>
  <div class="app-frame">
    <aside class="nav-rail">
      <div class="brand" aria-label="AI Finance Desk">
        <span class="brand-mark">AF</span>
        <span class="brand-name">Finance Desk</span>
      </div>

      <nav class="primary-nav" aria-label="主导航">
        <RouterLink v-for="item in navigation" :key="item.to" :to="item.to" class="nav-link">
          <component :is="item.icon" class="nav-icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="rail-status">
        <span class="status-dot" :class="{ online: system.backendConnected }" />
        <span>{{ system.backendConnected ? '本机服务在线' : '本机服务离线' }}</span>
      </div>
    </aside>

    <section class="app-body">
      <header class="status-strip">
        <div class="status-item">
          <span class="status-label">数据</span>
          <strong>{{ system.marketProvider || '等待连接' }}</strong>
        </div>
        <div class="status-item">
          <span class="status-label">模型</span>
          <strong>{{ system.modelConfigured ? system.deepModel : '未配置' }}</strong>
        </div>
        <div v-if="system.error" class="status-error">{{ system.error }}</div>
      </header>

      <main class="page-content">
        <RouterView />
      </main>
    </section>
  </div>
</template>

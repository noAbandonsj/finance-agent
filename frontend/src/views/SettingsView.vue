<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'

import { useSystemStore } from '@/stores/system'

const system = useSystemStore()
</script>

<template>
  <section class="page-section settings-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">LOCAL RUNTIME</p>
        <h1>系统设置</h1>
      </div>
      <el-tooltip content="刷新连接状态" placement="bottom">
        <el-button circle :icon="Refresh" :loading="system.loading" @click="system.load" />
      </el-tooltip>
    </div>

    <dl class="settings-list">
      <div>
        <dt>后端服务</dt>
        <dd :class="system.backendConnected ? 'value-ok' : 'value-warn'">
          {{ system.backendConnected ? '已连接' : '未连接' }}
        </dd>
      </div>
      <div>
        <dt>DeepSeek</dt>
        <dd :class="system.modelConfigured ? 'value-ok' : 'value-warn'">
          {{ system.modelConfigured ? '已配置' : '未配置' }}
        </dd>
      </div>
      <div>
        <dt>研究模型</dt>
        <dd>{{ system.deepModel || '-' }}</dd>
      </div>
      <div>
        <dt>行情源</dt>
        <dd>{{ system.marketProvider || '-' }}</dd>
      </div>
    </dl>
  </section>
</template>

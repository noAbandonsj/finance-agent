<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Delete, Plus, Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

import { useWatchlistStore } from '@/stores/watchlist'

const watchlist = useWatchlistStore()
const router = useRouter()
const symbol = ref('')

async function add(): Promise<void> {
  if (!symbol.value.trim()) return
  await watchlist.add(symbol.value.trim())
  symbol.value = ''
}

onMounted(() => watchlist.load())
</script>

<template>
  <section class="page-section">
    <div class="page-heading">
      <div>
        <p class="eyebrow">WATCHLIST</p>
        <h1>自选标的</h1>
      </div>
    </div>

    <form class="watchlist-toolbar" @submit.prevent="add">
      <el-input v-model="symbol" placeholder="输入股票或 ETF 代码" clearable />
      <el-button type="primary" native-type="submit" :icon="Plus">添加</el-button>
    </form>

    <el-table :data="watchlist.items" :loading="watchlist.loading" row-key="symbol">
      <el-table-column prop="symbol" label="代码" min-width="120" />
      <el-table-column prop="display_name" label="名称" min-width="150" />
      <el-table-column prop="security_type" label="类型" min-width="90" />
      <el-table-column label="最新价" min-width="100">
        <template #default="scope">{{ scope.row.snapshot?.last ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="行情时间" min-width="170">
        <template #default="scope">
          {{ scope.row.snapshot ? new Date(scope.row.snapshot.market_time).toLocaleString('zh-CN') : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="note" label="备注" min-width="150" show-overflow-tooltip />
      <el-table-column label="操作" width="112" fixed="right">
        <template #default="scope">
          <el-tooltip content="研究此标的">
            <el-button
              text
              circle
              :icon="Search"
              @click="router.push({ path: '/research', query: { symbol: scope.row.symbol } })"
            />
          </el-tooltip>
          <el-tooltip content="移出自选">
            <el-button text circle type="danger" :icon="Delete" @click="watchlist.remove(scope.row.symbol)" />
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

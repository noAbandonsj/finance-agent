import { createRouter, createWebHistory } from 'vue-router'

import HistoryView from '@/views/HistoryView.vue'
import ResearchView from '@/views/ResearchView.vue'
import SettingsView from '@/views/SettingsView.vue'
import WatchlistView from '@/views/WatchlistView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/research' },
    { path: '/research', name: 'research', component: ResearchView },
    { path: '/watchlist', name: 'watchlist', component: WatchlistView },
    { path: '/history', name: 'history', component: HistoryView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

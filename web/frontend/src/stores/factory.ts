import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getFactoryDashboard } from '../api'
import type { FactoryDashboard } from '../types/factory'

export const useFactoryStore = defineStore('factory', () => {
  const dashboard = ref<FactoryDashboard | null>(null)
  const loading = ref(false)
  const error = ref('')
  const lastLoadedAt = ref<number | null>(null)

  async function loadDashboard() {
    loading.value = true
    error.value = ''
    try {
      dashboard.value = await getFactoryDashboard()
      lastLoadedAt.value = Date.now()
    } catch (err: any) {
      error.value = err?.message || '工厂状态加载失败'
    } finally {
      loading.value = false
    }
  }

  async function refreshDashboard() {
    await loadDashboard()
  }

  return {
    dashboard,
    loading,
    error,
    lastLoadedAt,
    loadDashboard,
    refreshDashboard,
  }
})

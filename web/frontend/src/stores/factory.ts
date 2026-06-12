import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getFactoryDashboard, updateFactoryMode } from '../api'
import type { FactoryDashboard, FactoryMode } from '../types/factory'

export const useFactoryStore = defineStore('factory', () => {
  const dashboard = ref<FactoryDashboard | null>(null)
  const loading = ref(false)
  const savingMode = ref(false)
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

  async function saveMode(mode: FactoryMode) {
    savingMode.value = true
    error.value = ''
    try {
      await updateFactoryMode(mode)
      await loadDashboard()
    } catch (err: any) {
      error.value = err?.message || '生产模式保存失败'
      throw err
    } finally {
      savingMode.value = false
    }
  }

  return {
    dashboard,
    loading,
    savingMode,
    error,
    lastLoadedAt,
    loadDashboard,
    refreshDashboard,
    saveMode,
  }
})

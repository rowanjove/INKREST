import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getFactoryDashboard, getFactoryStudio, updateFactoryMode } from '../api'
import type { FactoryDashboard, FactoryMode } from '../types/factory'
import type { FactoryStudioDashboard } from '../types/studio'

export const useFactoryStore = defineStore('factory', () => {
  const dashboard = ref<FactoryDashboard | null>(null)
  const loading = ref(false)
  const savingMode = ref(false)
  const error = ref('')
  const lastLoadedAt = ref<number | null>(null)
  const studio = ref<FactoryStudioDashboard | null>(null)
  const studioLoading = ref(false)

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

  async function loadStudio() {
    studioLoading.value = true
    try {
      studio.value = await getFactoryStudio()
    } finally {
      studioLoading.value = false
    }
  }

  return {
    dashboard,
    loading,
    savingMode,
    error,
    lastLoadedAt,
    studio,
    studioLoading,
    loadDashboard,
    refreshDashboard,
    loadStudio,
    saveMode,
  }
})
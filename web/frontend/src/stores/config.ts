import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getConfig, updateConfig } from '../api'

export const useConfigStore = defineStore('config', () => {
  const config = ref<Record<string, unknown>>({})
  const loading = ref(false)

  async function fetchConfig() {
    loading.value = true
    try {
      const { data } = await getConfig()
      config.value = data
    } catch { /* backend warming up */ }
    finally { loading.value = false }
  }

  async function saveConfig(updates: Record<string, unknown>) {
    loading.value = true
    try {
      await updateConfig(updates)
      config.value = { ...config.value, ...updates }
    } finally { loading.value = false }
  }

  return { config, loading, fetchConfig, saveConfig }
})

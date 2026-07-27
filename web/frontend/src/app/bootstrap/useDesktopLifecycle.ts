import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'
import type { Router } from 'vue-router'

import { useTasksStore } from '../../stores/tasks'

export type BackendStatus = 'online' | 'offline' | 'restarting'

export function useDesktopLifecycle(router: Router, isPetRoute: Ref<boolean>) {
  const backendStatus = ref<BackendStatus>('online')
  const backendUnreachable = ref(false)
  const tasksStore = useTasksStore()
  let unlistenNavigate: (() => void) | null = null
  let unlistenBackendStatus: (() => void) | null = null
  let healthPollTimer: number | null = null
  let healthFailStreak = 0

  const healthUrl = () => {
    const origin = window.location.origin
    if (origin.includes('tauri') || origin.startsWith('file:')) {
      return 'http://127.0.0.1:8000/api/health'
    }
    return `${origin}/api/health`
  }

  const checkHealth = async () => {
    if (backendStatus.value === 'restarting') return
    try {
      const response = await fetch(healthUrl(), {
        signal: AbortSignal.timeout(8_000),
      })
      if (!response.ok) throw new Error('health not ok')
      healthFailStreak = 0
      backendUnreachable.value = false
      if (backendStatus.value === 'offline') backendStatus.value = 'online'
    } catch {
      healthFailStreak += 1
      if (healthFailStreak >= 2) {
        backendUnreachable.value = true
        if (!window.electronAPI) backendStatus.value = 'offline'
      }
    }
  }

  const refreshTasks = () => {
    void tasksStore.refreshTaskList()
  }

  onMounted(() => {
    if (isPetRoute.value) return
    tasksStore.connectElectronEvents()
    tasksStore.startPolling()
    window.addEventListener('inkrest-pipeline-started', refreshTasks)
    window.addEventListener('inkrest-batch-finished', refreshTasks)

    if (window.electronAPI?.onNavigate) {
      unlistenNavigate = window.electronAPI.onNavigate((path) => {
        void router.push(path)
      })
    }
    if (window.electronAPI?.onBackendStatus) {
      unlistenBackendStatus = window.electronAPI.onBackendStatus((status) => {
        backendStatus.value = status as BackendStatus
        backendUnreachable.value = status === 'offline'
      })
      void window.electronAPI.getBackendStatus().then((status) => {
        backendStatus.value = status as BackendStatus
        backendUnreachable.value = status === 'offline'
      })
    } else {
      void checkHealth()
      healthPollTimer = window.setInterval(() => void checkHealth(), 10_000)
    }
  })

  onBeforeUnmount(() => {
    window.removeEventListener('inkrest-pipeline-started', refreshTasks)
    window.removeEventListener('inkrest-batch-finished', refreshTasks)
    tasksStore.stopPolling()
    unlistenNavigate?.()
    unlistenBackendStatus?.()
    if (healthPollTimer !== null) window.clearInterval(healthPollTimer)
  })

  return { backendStatus, backendUnreachable, checkHealth }
}

import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useTasksStore } from '../stores/tasks'

export function useMonitorView() {
  const route = useRoute()
  const router = useRouter()
  const tasksStore = useTasksStore()
  const { isRunning, currentChapterId, lastTaskFailure } = storeToRefs(tasksStore)

  const activeTab = ref('task_logs')

  const syncTab = () => {
    if (route.query.tab === 'tasks') {
      router.replace('/chapters/maintenance')
      return
    }
    const tab = route.query.tab as string | undefined
    if (tab === 'interface_logs') {
      router.replace({ path: '/monitor', query: { ...route.query, tab: 'logs' } })
      return
    }
    const allowedTabs = ['task_logs', 'agent_logs', 'logs']
    if (tab && allowedTabs.includes(tab)) {
      activeTab.value = tab
    }
  }

  watch(activeTab, (newTab) => {
    router.replace({ query: { ...route.query, tab: newTab } })
  })

  watch(() => route.query.tab, () => {
    syncTab()
  })

  onMounted(() => {
    tasksStore.connectElectronEvents()
    tasksStore.startPolling()
    tasksStore.startRuntimeLogPolling()
    syncTab()
  })

  onUnmounted(() => {
    tasksStore.stopPolling()
    tasksStore.stopRuntimeLogPolling()
  })

  function dismissTaskFailure() {
    lastTaskFailure.value = null
  }

  return {
    isRunning,
    currentChapterId,
    lastTaskFailure,
    activeTab,
    dismissTaskFailure,
  }
}
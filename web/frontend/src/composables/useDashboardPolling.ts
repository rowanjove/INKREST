import { type Ref } from 'vue'
import { shouldPoll } from '../utils/pollingGate'
import { useChapterStore } from '../stores/chapter'
import { useFactoryStore } from '../stores/factory'
import { useTasksStore } from '../stores/tasks'

export function useDashboardPolling(options: {
  activeTab: Ref<string>
  loadSerialData: () => Promise<void>
}) {
  const { activeTab, loadSerialData } = options
  const chapterStore = useChapterStore()
  const factoryStore = useFactoryStore()
  const tasksStore = useTasksStore()

  let timer: number | undefined

  function restartDashboardTimer() {
    if (timer) window.clearInterval(timer)
    const intervalMs = tasksStore.isRunning ? 3000 : 15000
    timer = window.setInterval(() => {
      if (!shouldPoll()) return
      if (tasksStore.isRunning) {
        chapterStore.refreshAll()
        void factoryStore.refreshDashboard()
      }
      if (activeTab.value === 'serialization') {
        void loadSerialData()
      }
    }, intervalMs)
  }

  function stopDashboardPolling() {
    if (timer) window.clearInterval(timer)
    timer = undefined
  }

  return { restartDashboardTimer, stopDashboardPolling, tasksStore }
}
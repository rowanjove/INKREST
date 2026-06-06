import { onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { usePipelineAlertsStore, formatAlertStage } from '../stores/pipelineAlerts'

export type { PipelineAlert } from '../stores/pipelineAlerts'
export { formatAlertStage }

export function usePipelineAlerts(pollIntervalMs = 4000) {
  const store = usePipelineAlertsStore()
  const { alerts: pipelineAlerts, loading } = storeToRefs(store)

  onMounted(() => store.startPolling(pollIntervalMs))
  onUnmounted(() => store.stopPolling())

  return {
    pipelineAlerts,
    loading,
    loadPipelineAlerts: store.fetchAlerts,
    formatAlertStage: store.formatAlertStage,
  }
}
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPipelineAlerts } from '../api'
import { shouldPoll } from '../utils/pollingGate'

export type PipelineAlert = {
  chapter_id: string
  last_stage: string
  message: string
  completed_stages?: string[]
  timestamp?: string
  quality?: {
    mode?: string
    overall_pass?: boolean
    overall_status?: string
    blocked_by?: string[]
  }
}

export function formatAlertStage(stage: string) {
  if (stage === 'quality_blocked') return '质量阻断'
  if (stage === 'approval_rejected') return '审批拒绝'
  if (stage === 'batch_retry') return '批量跳过·待重试'
  if (stage === 'external_review_pending') return '待外审'
  return stage
}

export const usePipelineAlertsStore = defineStore('pipelineAlerts', () => {
  const alerts = ref<PipelineAlert[]>([])
  const loading = ref(false)
  let timer: number | null = null
  let subscribers = 0

  async function fetchAlerts() {
    if (!shouldPoll()) return
    loading.value = true
    try {
      const { data } = await getPipelineAlerts()
      alerts.value = (data.alerts || []) as PipelineAlert[]
    } catch {
      alerts.value = []
    } finally {
      loading.value = false
    }
  }

  function startPolling(intervalMs = 4000) {
    subscribers += 1
    if (subscribers === 1) {
      fetchAlerts()
      timer = window.setInterval(fetchAlerts, intervalMs)
    }
  }

  function stopPolling() {
    subscribers = Math.max(0, subscribers - 1)
    if (subscribers === 0 && timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  return {
    alerts,
    loading,
    fetchAlerts,
    startPolling,
    stopPolling,
    formatAlertStage,
  }
})
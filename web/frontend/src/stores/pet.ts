import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  getAssistantContext,
  sendAssistantChat,
  getAssistantDiagnose,
  fixAssistantIssue
} from '../api'
import {
  SHANSHAN_CHAT_ERROR,
  SHANSHAN_FIX_REPLY,
  SHANSHAN_WELCOME_CHAT,
} from '../constants/shanshanCopy'
import { isPipelineRunning, mapContextToPetState, type PetState } from '../utils/petState'
import { formatTaskStep } from '../utils/taskStepLabels'

export type { PetState }

export interface PetSettings {
  enabled: boolean
  showOnStartup: boolean
  alwaysOnTop: boolean
  size: number
  position: { x: number; y: number } | null
  notifyOnTaskComplete: boolean
  notifyOnTaskError: boolean
  petId: string
}

export interface AssistantTaskSummary {
  id: string
  status: string
  chapter_id?: string
  goal?: string
  error?: string
  step?: string
  gate_summary?: string
}

export interface AssistantWorkSnapshot {
  scale: string
  scale_label: string
  target_chapters: number
  chapters_written: number
  has_macro_outline: boolean
}

export interface NovelBatchSummary {
  paused: boolean
  pause_reason?: string
  last_arc_id?: string
  last_chapter_id?: string
  fail_streak?: number
}

export interface AssistantContext {
  backend_health: 'ok' | string
  active_project: { id: string; name: string } | null
  work?: AssistantWorkSnapshot
  running_tasks: AssistantTaskSummary[]
  failed_tasks: AssistantTaskSummary[]
  recent_logs: Array<{ level: string; message: string; chapter_id?: string; task_id?: string; source?: string; step?: string }>
  agent_runtime_logs?: Array<{
    id?: number
    level: string
    message: string
    step?: string
    chapter_id?: string
    source?: string
    timestamp?: number
  }>
  system_log_tail?: string[]
  system_log_paths?: Record<string, string>
  novel_batch?: NovelBatchSummary
  pipeline_active?: boolean
  pipeline_pending?: {
    pending_total?: number
    pending_retry_count?: number
    pending_gate_count?: number
  }
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  actions?: Array<{ type: string; label: string; payload?: any }>
  timestamp: number
}

export interface DiagnoseIssue {
  code: string
  level: 'info' | 'warning' | 'error'
  message: string
}

export interface DiagnoseResult {
  status: 'ok' | 'warning' | 'error'
  issues: DiagnoseIssue[]
  suggestions: Array<{ label: string; type: string; payload?: any }>
}

const defaultSettings: PetSettings = {
  enabled: true,
  showOnStartup: true,
  alwaysOnTop: true,
  size: 180,
  position: null,
  notifyOnTaskComplete: true,
  notifyOnTaskError: true,
  petId: 'shanshan',
}

export const usePetStore = defineStore('pet', () => {
  const ignoredFailedTasksKey = 'pet_ignored_failed_tasks'
  const settings = ref<PetSettings>({ ...defaultSettings })
  const context = ref<AssistantContext | null>(null)
  const state = ref<PetState>('idle')
  const loading = ref(false)
  const lastError = ref('')
  let pollTimer: number | null = null
  let flashTimer: number | null = null
  let wasPipelineRunning = false
  let lastActiveFailedCount = 0

  function readIgnoredFailedTaskIds() {
    try {
      const stored = JSON.parse(localStorage.getItem(ignoredFailedTasksKey) || '[]')
      return Array.isArray(stored) ? stored.filter((id): id is string => typeof id === 'string') : []
    } catch {
      return []
    }
  }

  const ignoredFailedTaskIds = ref<string[]>(readIgnoredFailedTaskIds())

  // ---- Chat Q&A State ----
  const chatHistory = ref<ChatMessage[]>([])
  const chatLoading = ref(false)

  // ---- System Diagnosis State ----
  const diagnoseResult = ref<DiagnoseResult | null>(null)
  const diagnoseLoading = ref(false)

  const novelBatchPaused = computed(() => Boolean(context.value?.novel_batch?.paused))

  const statusLabel = computed(() => {
    if (novelBatchPaused.value) return '全书已暂停'
    if (state.value === 'working') return '正在生成'
    if (state.value === 'success') return '任务完成'
    if (state.value === 'error') return '遇到错误'
    if (state.value === 'question') return '疑惑'
    if (state.value === 'offline') return '后端离线'
    if (state.value === 'dragging') return '移动中'
    if (state.value.startsWith('hide-')) return '已贴边隐藏'
    return '待命'
  })

  const workProgressLine = computed(() => {
    const w = context.value?.work
    if (!w || (!w.scale_label && !w.scale && !w.chapters_written)) return ''
    const label = w.scale_label || w.scale || '未设定体量'
    const target = w.target_chapters > 0 ? `/${w.target_chapters}` : ''
    return `${label} · 已写 ${w.chapters_written}${target} 章`
  })

  const statusDetail = computed(() => {
    if (lastError.value) return lastError.value
    const batch = context.value?.novel_batch
    if (batch?.paused) {
      const reason = batch.pause_reason || 'circuit_breaker'
      const arc = batch.last_arc_id || '—'
      const ch = batch.last_chapter_id || '—'
      const streak =
        batch.fail_streak && batch.fail_streak > 0 ? `，连续失败 ${batch.fail_streak} 次` : ''
      return `批量暂停（${reason}，卷 ${arc} / 章 ${ch}${streak}）`
    }
    const running = context.value?.running_tasks?.[0]
    if (running) {
      const stepLabel = formatTaskStep(running.step)
      return `${running.chapter_id || '章节'} · ${stepLabel}`
    }
    if (latestFailedTask.value) {
      const gate = latestFailedTask.value.gate_summary
      const err = latestFailedTask.value.error || '章节任务失败'
      return gate ? `${err} · ${gate}` : err
    }
    const pendingTotal = context.value?.pipeline_pending?.pending_total ?? 0
    if (pendingTotal > 0) {
      return `${pendingTotal} 章待处理修章，可到章节维护查看。`
    }
    if (workProgressLine.value) return workProgressLine.value
    return '助手正在待命，有任务动态会及时提醒。'
  })

  const latestFailedTask = computed(() => {
    const failed = (context.value?.failed_tasks || []).filter(
      (t) => t.id && !ignoredFailedTaskIds.value.includes(t.id),
    )
    return failed.length ? failed[failed.length - 1] : null
  })

  /** 气泡窗指示灯：贴边隐藏时仍反映真实流水线状态 */
  const bubblePulseState = computed((): PetState => {
    const current = state.value
    if (current.startsWith('hide-')) {
      return mapContextToState(context.value)
    }
    return current
  })

  function mapContextToState(next: AssistantContext | null): PetState {
    return mapContextToPetState(next, ignoredFailedTaskIds.value)
  }

  function countActiveFailed(next: AssistantContext | null): number {
    if (!next) return 0
    return (next.failed_tasks || []).filter(
      (t) => t.id && !ignoredFailedTaskIds.value.includes(t.id),
    ).length
  }

  function clearFlashTimer() {
    if (flashTimer) {
      window.clearTimeout(flashTimer)
      flashTimer = null
    }
  }

  function flashTransientState(next: AssistantContext, flash: 'success' | 'error') {
    if (isHiddenAtEdge.value) return
    if (flash === 'success' && !settings.value.notifyOnTaskComplete) {
      state.value = mapContextToState(next)
      return
    }
    if (flash === 'error' && !settings.value.notifyOnTaskError) {
      state.value = mapContextToState(next)
      return
    }
    clearFlashTimer()
    state.value = flash
    flashTimer = window.setTimeout(() => {
      state.value = mapContextToState(context.value)
      flashTimer = null
    }, 4000)
  }

  function applyContextState(next: AssistantContext) {
    const running = isPipelineRunning(next)
    const activeFailed = countActiveFailed(next)
    const steady = mapContextToState(next)

    if (isHiddenAtEdge.value) {
      wasPipelineRunning = running
      lastActiveFailedCount = activeFailed
      return
    }

    if (flashTimer) {
      wasPipelineRunning = running
      lastActiveFailedCount = activeFailed
      return
    }

    if (running) {
      wasPipelineRunning = true
      state.value = steady
    } else if (wasPipelineRunning) {
      wasPipelineRunning = false
      const batchPaused = Boolean(next.novel_batch?.paused)
      if (activeFailed > 0 || batchPaused) {
        flashTransientState(next, 'error')
      } else {
        flashTransientState(next, 'success')
      }
    } else if (activeFailed > lastActiveFailedCount) {
      flashTransientState(next, 'error')
    } else {
      state.value = steady
    }

    lastActiveFailedCount = activeFailed
  }

  function ignoreFailedTask(taskId: string) {
    // 批量忽略当前所有的失败任务，从而彻底清空错误状态
    const failedIds = context.value?.failed_tasks.map(t => t.id) || []
    if (failedIds.length > 0) {
      failedIds.forEach(id => {
        if (!ignoredFailedTaskIds.value.includes(id)) {
          ignoredFailedTaskIds.value.push(id)
        }
      })
    } else if (!ignoredFailedTaskIds.value.includes(taskId)) {
      ignoredFailedTaskIds.value.push(taskId)
    }
    localStorage.setItem(ignoredFailedTasksKey, JSON.stringify(ignoredFailedTaskIds.value))
    clearFlashTimer()
    if (context.value) {
      applyContextState(context.value)
    } else {
      state.value = mapContextToState(context.value)
    }
    runDiagnose() // Re-run diagnose immediately to filter ignored issues
  }

  async function loadSettings() {
    if (!window.electronAPI?.getPetSettings) {
      settings.value = { ...defaultSettings }
      return settings.value
    }
    settings.value = await window.electronAPI.getPetSettings()
    return settings.value
  }

  async function updateSettings(patch: Partial<PetSettings>) {
    if (!window.electronAPI?.updatePetSettings) {
      settings.value = { ...settings.value, ...patch }
      return settings.value
    }
    settings.value = await window.electronAPI.updatePetSettings(patch)
    return settings.value
  }

  const isHiddenAtEdge = ref<'left' | 'right' | 'top' | 'bottom' | null>(null)

  function syncIgnoredFailedTasks(event?: StorageEvent) {
    if (event && event.key !== ignoredFailedTasksKey) return
    ignoredFailedTaskIds.value = readIgnoredFailedTaskIds()
    if (!isHiddenAtEdge.value && context.value) {
      clearFlashTimer()
      applyContextState(context.value)
    }
  }

  async function refreshContext() {
    loading.value = true
    try {
      const { data } = await getAssistantContext()
      context.value = data
      applyContextState(data)
      lastError.value = ''
    } catch (error: any) {
      context.value = null
      if (!isHiddenAtEdge.value) {
        state.value = 'offline'
      }
      lastError.value = error?.message || '无法连接后端'
    } finally {
      loading.value = false
    }
  }

  function setDragging(dragging: boolean) {
    if (dragging) {
      state.value = 'dragging'
    } else {
      if (isHiddenAtEdge.value) {
        state.value = `hide-${isHiddenAtEdge.value}`
      } else {
        state.value = mapContextToState(context.value)
      }
    }
  }

  function setHiddenAtEdge(edge: 'left' | 'right' | 'top' | 'bottom' | null) {
    isHiddenAtEdge.value = edge
    if (edge) {
      state.value = `hide-${edge}`
    } else {
      state.value = mapContextToState(context.value)
    }
  }

  function startPolling() {
    if (pollTimer) return
    syncIgnoredFailedTasks()
    window.addEventListener('storage', syncIgnoredFailedTasks)
    refreshContext()
    pollTimer = window.setInterval(refreshContext, 2500)
  }

  function stopPolling() {
    window.removeEventListener('storage', syncIgnoredFailedTasks)
    clearFlashTimer()
    if (pollTimer) {
      window.clearInterval(pollTimer)
      pollTimer = null
    }
  }

  // ---- Chat Q&A Actions ----

  function initChatHistory() {
    if (chatHistory.value.length === 0) {
      chatHistory.value.push({
        role: 'assistant',
        content: SHANSHAN_WELCOME_CHAT,
        timestamp: Date.now()
      })
    }
  }

  async function sendChatMessage(message: string) {
    if (!message.trim() || chatLoading.value) return
    chatLoading.value = true

    // Add user message to history
    chatHistory.value.push({
      role: 'user',
      content: message,
      timestamp: Date.now()
    })

    try {
      // Build API history
      const apiHistory = chatHistory.value.map(h => ({
        role: h.role,
        content: h.content
      }))

      const { data } = await sendAssistantChat({
        message,
        history: apiHistory
      })

      chatHistory.value.push({
        role: 'assistant',
        content: data.reply,
        actions: data.actions || [],
        timestamp: Date.now()
      })
    } catch (error: any) {
      chatHistory.value.push({
        role: 'assistant',
        content: SHANSHAN_CHAT_ERROR(error?.message || '未知网络错误'),
        timestamp: Date.now()
      })
    } finally {
      chatLoading.value = false
    }
  }

  function clearChatHistory() {
    chatHistory.value = []
    initChatHistory()
  }

  // ---- Diagnosis & Fix Actions ----

  async function runDiagnose() {
    diagnoseLoading.value = true
    try {
      const { data } = await getAssistantDiagnose(ignoredFailedTaskIds.value)
      diagnoseResult.value = data
    } catch (error: any) {
      diagnoseResult.value = {
        status: 'error',
        issues: [
          {
            code: 'DIAGNOSE_FAILED',
            level: 'error',
            message: `诊断运行失败：${error?.message || '网络连接异常'}`
          }
        ],
        suggestions: []
      }
    } finally {
      diagnoseLoading.value = false
    }
  }

  async function executeFix(fixType: string, payload: any) {
    chatHistory.value.push({
      role: 'user',
      content: `[快捷操作] 执行修复动作: ${
        fixType === 'test_model'
          ? '测试模型连通性'
          : fixType === 'retry_task'
          ? `重试第 ${payload.chapter_id} 章任务`
          : '执行建议操作'
      }`,
      timestamp: Date.now()
    })

    chatLoading.value = true
    try {
      const { data } = await fixAssistantIssue({ fix_type: fixType, payload })
      if (data.success) {
        let replyText = ''
        if (fixType === 'test_model') {
          const details = data.details || {}
          replyText = SHANSHAN_FIX_REPLY.testModelOk(
            details.latency_ms ?? 0,
            details.response_preview ?? ''
          )
        } else if (fixType === 'retry_task') {
          replyText = SHANSHAN_FIX_REPLY.retryTaskOk
          setTimeout(refreshContext, 500)
        } else {
          replyText = data.message || '操作已完成。'
        }
        chatHistory.value.push({
          role: 'assistant',
          content: replyText,
          timestamp: Date.now()
        })
      } else {
        chatHistory.value.push({
          role: 'assistant',
          content: SHANSHAN_FIX_REPLY.fixFailed(data.error || '未知错误'),
          timestamp: Date.now()
        })
      }
    } catch (error: any) {
      chatHistory.value.push({
        role: 'assistant',
        content: SHANSHAN_FIX_REPLY.fixError(error?.message || '网络通讯故障'),
        timestamp: Date.now()
      })
    } finally {
      chatLoading.value = false
      runDiagnose() // Re-run diagnosis to refresh
    }
  }

  return {
    settings,
    context,
    state,
    bubblePulseState,
    loading,
    lastError,
    statusLabel,
    statusDetail,
    workProgressLine,
    novelBatchPaused,
    latestFailedTask,
    chatHistory,
    chatLoading,
    diagnoseResult,
    diagnoseLoading,
    loadSettings,
    updateSettings,
    refreshContext,
    setDragging,
    startPolling,
    stopPolling,
    initChatHistory,
    sendChatMessage,
    clearChatHistory,
    runDiagnose,
    executeFix,
    ignoredFailedTaskIds,
    ignoreFailedTask,
    isHiddenAtEdge,
    setHiddenAtEdge,
  }
})

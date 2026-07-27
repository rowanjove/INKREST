import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { abortTask as apiAbortTask, clearRuntimeLogs } from '../api'
import { formatFailureDetail, normalizeFailureDetail } from '../utils/errorCodes'

function pulsePetPipelineRefresh() {
  try {
    new BroadcastChannel('inkrest-pipeline').postMessage({ type: 'pulse', at: Date.now() })
  } catch {
    /* BroadcastChannel unavailable */
  }
}
import { createRuntimeLogTransport, createTaskListTransport } from '../composables/useTaskProgress'
import { PRODUCTION_BLOCKS } from '../constants/pipelineDisplay'
import { chapterHasGateFailure } from '../utils/productionLineBlocks'
import { usePipelineAlertsStore } from './pipelineAlerts'

export interface LogEntry {
  timestamp: number
  step: string
  message: string
  level: 'info' | 'warn' | 'error' | 'debug'
  chapter_id?: string
}

export interface ProgressEntry {
  step: string
  status: 'running' | 'done' | 'error' | 'skipped' | 'warning' | 'blocked'
  chapter_id: string
  data?: Record<string, any>
  timestamp: number
}

export interface TaskSummary {
  task_id: string
  chapter_id?: string
  status: 'pending' | 'claimed' | 'running' | 'paused' | 'succeeded' | 'failed' | 'cancelled'
  goal?: string
  error?: string
  created_at?: string
  updated_at?: string
  progress?: {
    step: string
    status: ProgressEntry['status']
    chapter_id?: string
    data?: Record<string, any>
    timestamp?: number
  }
  result?: {
    code?: string
    failure_kind?: string
    failure_hint?: string
    message?: string
    retryable?: boolean
    user_action?: string
    resumable_from?: string
  }
  failure_kind?: string
  error_code?: string
  retryable?: boolean
  user_action?: string
  resumable_from?: string
  status_reason?: string
  last_heartbeat?: string
}

const STEP_LABELS: Record<string, string> = {
  init: '初始化',
  chapter_planner: '章节规划',
  planner: '规划',
  writer: '写作',
  merge: '合并',
  stitch_editor: '接缝修复',
  style_editor: '文风优化',
  continuity_checker: '连续性检查',
  chapter_summary: '章节总结',
  auditor: '审校',
  state_extractor: '状态提取',
  rewriter: '改写',
  length_fix: '字数修复',
  unified_gate: '统一门禁',
  quality_guard: '质量门禁',
  approval: '审批',
  sensitive_scan: '敏感词扫描',
  state_update: '状态同步',
  vector_index: '向量索引',
  plugin_hook: '插件钩子',
  complete: '完成',
  error: '错误',
  abort: '中止',
  ensure_queue: '同步卷队列',
  managing_editor: '主编拆卷',
}

function normalizeLogLevel(level: string | undefined, message: string): LogEntry['level'] {
  const raw = (level || '').toLowerCase()
  if (raw === 'warn' || raw === 'warning') return 'warn'
  if (raw === 'debug') return 'debug'
  if (raw === 'error') {
    const m = message.trim()
    if (/\b(INFO|DEBUG|TRACE)\b/i.test(m) && !/\b(ERROR|CRITICAL|FATAL|Exception|Traceback)\b/i.test(m)) {
      return 'info'
    }
    if (/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}.*\sINFO\s/i.test(m)) return 'info'
    if (/uvicorn\.|Started server|Application startup/i.test(m)) return 'info'
    return 'error'
  }
  return 'info'
}

function progressStatusToLogLevel(status: string): LogEntry['level'] {
  if (status === 'error') return 'error'
  if (status === 'warning' || status === 'blocked') return 'warn'
  return 'info'
}

function formatProgressLogMessage(entry: ProgressEntry): string {
  const stepLabel = STEP_LABELS[entry.step] || entry.step
  const status = entry.status
  if (status === 'running') return `${stepLabel} 执行中…`
  if (status === 'done') return `${stepLabel} 完成`
  if (status === 'skipped') return `${stepLabel} 已跳过`
  if (status === 'warning') return `${stepLabel} 警告`
  if (status === 'blocked') return `${stepLabel} 已阻断`
  if (status === 'error') return `${stepLabel} 失败`
  return `${stepLabel} · ${status}`
}

const QUEUE_PROGRESS_STEPS = new Set(['ensure_queue', 'managing_editor', 'novel_batch', 'novel_autopilot'])

const PIPELINE_ORDER = [
  'init',
  'chapter_planner',
  'planner',
  'writer',
  'merge',
  'stitch_editor',
  'style_editor',
  'continuity_checker',
  'chapter_summary',
  'auditor',
  'state_extractor',
  'rewriter',
  'length_fix',
  'unified_gate',
  'quality_guard',
  'approval',
  'sensitive_scan',
  'state_update',
  'vector_index',
  'plugin_hook',
]

export const useTasksStore = defineStore('tasks', () => {
  const logs = shallowRef<LogEntry[]>([])
  const taskList = shallowRef<TaskSummary[]>([])
  const progress = ref<ProgressEntry[]>([])
  const currentChapterId = ref<string>('')
  const currentTaskId = ref<string>('')
  const isRunning = ref(false)
  const lastTaskFailure = ref<{ task_id: string; hint: string; code: string } | null>(null)

  function addLog(entry: LogEntry) {
    const next = [...logs.value, entry]
    logs.value = next.length > 500 ? next.slice(-500) : next
  }

  const lastProgressLogKey = ref('')

  function addProgress(entry: ProgressEntry) {
    const logKey = `${entry.chapter_id}:${entry.step}:${entry.status}`
    if (logKey !== lastProgressLogKey.value && entry.step) {
      lastProgressLogKey.value = logKey
      addLog({
        timestamp: entry.timestamp || Date.now(),
        step: entry.step,
        message: formatProgressLogMessage(entry),
        level: progressStatusToLogLevel(entry.status),
        chapter_id: entry.chapter_id,
      })
    }

    // If the step is running, mark all preceding steps in the pipeline order as done
    if (entry.status === 'running') {
      const currentIdx = PIPELINE_ORDER.indexOf(entry.step)
      if (currentIdx >= 0) {
        const preceding = PIPELINE_ORDER.slice(0, currentIdx)
        progress.value.forEach(p => {
          if (p.chapter_id === entry.chapter_id && preceding.includes(p.step) && p.status === 'running') {
            p.status = 'done'
          }
        })
        // 章节流水线启动后，卷队列同步不应继续占着 S1
        progress.value.forEach((p) => {
          if (QUEUE_PROGRESS_STEPS.has(p.step) && p.status === 'running') {
            p.status = 'done'
          }
        })
      }
    }

    if (entry.step === 'ensure_queue' && entry.status === 'done') {
      progress.value.forEach((p) => {
        if (p.step === 'ensure_queue' && p.status === 'running') {
          p.status = 'done'
        }
      })
    }

    const idx = progress.value.findIndex(
      p => p.step === entry.step && p.chapter_id === entry.chapter_id
    )
    if (idx >= 0) {
      progress.value[idx] = entry
    } else {
      progress.value.push(entry)
    }

    if (entry.status === 'running') {
      isRunning.value = true
      currentChapterId.value = entry.chapter_id
      if (PIPELINE_ORDER.includes(entry.step) || QUEUE_PROGRESS_STEPS.has(entry.step)) {
        pulsePetPipelineRefresh()
      }
    }

    if (
      entry.step === 'quality_guard' &&
      (entry.status === 'blocked' || entry.status === 'warning')
    ) {
      try {
        usePipelineAlertsStore().fetchAlerts()
      } catch {
        /* optional */
      }
    }
  }

  const GATE_STEPS = PRODUCTION_BLOCKS.find((block) => block.id === 'gate')?.steps ?? []

  function ensureGateProgressDone(chapterId: string) {
    if (!chapterId || chapterHasGateFailure(progress.value, chapterId)) return
    const now = Date.now()
    for (const step of GATE_STEPS) {
      const idx = progress.value.findIndex(
        (entry) => entry.chapter_id === chapterId && entry.step === step,
      )
      if (idx < 0) {
        progress.value.push({
          step,
          status: 'done',
          chapter_id: chapterId,
          timestamp: now,
        })
      } else if (progress.value[idx].status === 'running') {
        progress.value[idx] = { ...progress.value[idx], status: 'done', timestamp: now }
      }
    }
  }

  function markComplete(chapterId: string) {
    progress.value.forEach(p => {
      if (p.chapter_id === chapterId && p.status === 'running') {
        p.status = 'done'
      }
      if (!p.chapter_id && QUEUE_PROGRESS_STEPS.has(p.step) && p.status === 'running') {
        p.status = 'done'
      }
    })
    ensureGateProgressDone(chapterId)
    const hasOtherRunning = progress.value.some(
      (entry) => entry.status === 'running' && entry.chapter_id !== chapterId,
    )
    if (!hasOtherRunning) {
      isRunning.value = false
    }
    try {
      usePipelineAlertsStore().fetchAlerts()
    } catch {
      /* store optional during tests */
    }
    addLog({
      timestamp: Date.now(),
      step: 'complete',
      message: `章节 ${chapterId} 生成完成`,
      level: 'info',
      chapter_id: chapterId,
    })
  }

  function markError(chapterId: string, error: string) {
    isRunning.value = false
    progress.value.forEach(p => {
      if (p.chapter_id === chapterId && p.status === 'running') {
        p.status = 'error'
      }
    })
    addLog({
      timestamp: Date.now(),
      step: 'error',
      message: error,
      level: 'error',
      chapter_id: chapterId,
    })
  }

  const lastRuntimeLogId = ref(0)

  function ingestRuntimeLog(row: {
    id?: number
    timestamp?: number
    level?: string
    step?: string
    message?: string
    chapter_id?: string
    type?: string
    status?: string
  }) {
    if (row.id != null && row.id <= lastRuntimeLogId.value) return
    if (row.id != null) lastRuntimeLogId.value = Math.max(lastRuntimeLogId.value, row.id)
    const ts = row.timestamp
    const timestamp =
      typeof ts === 'number' ? (ts > 1e12 ? ts : ts * 1000) : Date.now()
    const rowType = row.type || 'log'
    const chapterId = row.chapter_id || ''

    if (rowType === 'progress' && row.step) {
      const status = (row.status || 'running') as ProgressEntry['status']
      addProgress({
        step: row.step,
        status,
        chapter_id: chapterId,
        timestamp,
      })
      return
    }

    if (rowType === 'complete' && chapterId) {
      markComplete(chapterId)
      return
    }

    addLog({
      timestamp,
      step: row.step || '',
      message: row.message || '',
      level: normalizeLogLevel(row.level, row.message || ''),
      chapter_id: chapterId,
    })
  }

  async function clearLogs() {
    logs.value = []
    progress.value = []
    lastProgressLogKey.value = ''
    lastRuntimeLogId.value = 0
    try {
      await clearRuntimeLogs()
    } catch {
      /* ignore */
    }
  }

  function isNovelPipelineTask(task: TaskSummary): boolean {
    const tid = String(task.task_id || '')
    const goal = String(task.goal || '')
    return tid.startsWith('novel-') || goal.startsWith('Novel')
  }

  function isAutoResumablePendingTask(task: TaskSummary): boolean {
    if (task.status !== 'pending' || !task.chapter_id) return false
    const goal = String(task.goal || '')
    return !(
      goal.startsWith('batch:') ||
      goal.startsWith('gate_only:') ||
      goal.startsWith('Novel:') ||
      goal.startsWith('Arc batch:')
    )
  }

  function processTasksList(data: TaskSummary[]) {
      taskList.value = data.slice()
      let runningFound = false
      for (const task of data) {
        if (task.status === 'running' || task.status === 'claimed') {
          runningFound = true
          currentTaskId.value = task.task_id
          if (task.chapter_id) {
            currentChapterId.value = task.chapter_id
          }
          isRunning.value = true
          if (task.progress) {
            addProgress({
              step: task.progress.step,
              status: task.progress.status,
              chapter_id: task.progress.chapter_id || task.chapter_id || '',
              data: task.progress.data,
              timestamp: (task.progress.timestamp ?? 0) * 1000,
            })
          }
        } else if (task.status === 'pending' && (isNovelPipelineTask(task) || isAutoResumablePendingTask(task))) {
          runningFound = true
          currentTaskId.value = task.task_id
          if (task.chapter_id) {
            currentChapterId.value = task.chapter_id
          }
          isRunning.value = true
        } else if (task.status === 'succeeded') {
          if (task.task_id === currentTaskId.value) {
            if (task.chapter_id) {
              progress.value.forEach(p => {
                if (p.chapter_id === task.chapter_id && p.status === 'running') {
                  p.status = 'done'
                }
              })
            }
            if (isRunning.value && currentChapterId.value === task.chapter_id) {
              markComplete(task.chapter_id)
            }
          }
        } else if (task.status === 'failed' || task.status === 'cancelled') {
          if (task.task_id === currentTaskId.value) {
            if (task.chapter_id) {
              progress.value.forEach(p => {
                if (p.chapter_id === task.chapter_id && p.status === 'running') {
                  p.status = 'error'
                }
              })
            }
            const fr = task.result || {}
            const detail = normalizeFailureDetail({ ...fr, error: task.error }, '任务执行失败')
            const hint = formatFailureDetail(detail)
            lastTaskFailure.value = { task_id: task.task_id, hint: String(hint), code: String(detail.code) }
            if (isRunning.value && currentChapterId.value === task.chapter_id) {
              markError(task.chapter_id || '', hint)
            }
          }
        }
      }
      const hasLocalRunningProgress = progress.value.some((p) => p.status === 'running')
      if (!runningFound && !hasLocalRunningProgress) {
        if (isRunning.value) {
          isRunning.value = false
        }
        currentTaskId.value = ''
      }
  }

  const taskListTransport = createTaskListTransport({
    onTasksList: processTasksList,
    onProgressMessage: (payload) => {
      ingestRuntimeLog(payload)
    }
  })
  const runtimeLogTransport = createRuntimeLogTransport({
    onRuntimeLog: ingestRuntimeLog,
    getLastLogId: () => lastRuntimeLogId.value,
    setLastLogId: (id) => {
      lastRuntimeLogId.value = id
    },
  })

  function startPolling() {
    taskListTransport.start()
  }

  function stopPolling() {
    taskListTransport.stop()
  }

  async function refreshTaskList() {
    await taskListTransport.refresh()
  }

  function startRuntimeLogPolling() {
    runtimeLogTransport.start()
  }

  function stopRuntimeLogPolling() {
    runtimeLogTransport.stop()
  }

  let electronEventsBound = false

  // Connect to Electron IPC events if available
  function connectElectronEvents() {
    const api = (window as any).electronAPI
    if (api && !electronEventsBound) {
      electronEventsBound = true
      api.onLog((data: any) => {
        const message = data.message || ''
        addLog({
          timestamp: (data.timestamp || Date.now() / 1000) * 1000,
          step: data.step || '',
          message,
          level: normalizeLogLevel(data.level, message),
          chapter_id: data.chapter_id,
        })
      })
      api.onProgress?.((data: any) => {
        if (data?.type === 'progress' && data.step) {
          addProgress({
            step: data.step,
            status: data.status || 'running',
            chapter_id: data.chapter_id || '',
            data: data.data,
            timestamp: (data.timestamp || Date.now() / 1000) * 1000,
          })
        }
      })
      api.onError?.((data: any) => {
        markError(data.chapter_id || '', data.error || '任务执行失败')
      })
      api.onComplete?.((data: any) => {
        if (data.chapter_id) markComplete(data.chapter_id)
      })
    }
  }

  async function abortCurrentTask() {
    if (!currentTaskId.value) return
    try {
      await apiAbortTask(currentTaskId.value)
      addLog({
        timestamp: Date.now(),
        step: 'abort',
        message: '已发送中止信号，正在中断生成章节...',
        level: 'warn',
        chapter_id: currentChapterId.value,
      })
    } catch (e) {
      console.error('Failed to abort task:', e)
    }
  }

  return {
    logs,
    taskList,
    progress,
    currentChapterId,
    currentTaskId,
    isRunning,
    lastTaskFailure,
    addLog,
    addProgress,
    markComplete,
    markError,
    clearLogs,
    connectElectronEvents,
    startPolling,
    stopPolling,
    startRuntimeLogPolling,
    stopRuntimeLogPolling,
    abortCurrentTask,
    refreshTaskList,
  }
})

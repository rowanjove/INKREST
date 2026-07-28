import { listTasks, getRuntimeLogs } from '../api'
import {
  buildTasksWebSocketUrl,
  RUNTIME_LOG_POLL_INTERVAL_MS,
  TASK_POLL_INTERVAL_MS,
  TASK_WS_BACKUP_POLL_MS,
  TASK_WS_HEARTBEAT_MS,
  TASK_WS_RECONNECT_MS,
} from './useTaskTransport'
import { shouldPoll } from '../utils/pollingGate'
import type { TaskSummary } from '../stores/tasks'

export type RuntimeLogRow = {
  id?: number
  timestamp?: number
  level?: string
  step?: string
  message?: string
  chapter_id?: string
  type?: string
  status?: string
}

type TaskListTransportOptions = {
  onTasksList: (tasks: TaskSummary[]) => void
  onProgressMessage?: (msg: any) => void
}

type RuntimeLogTransportOptions = {
  onRuntimeLog: (row: RuntimeLogRow) => void
  getLastLogId: () => number
  setLastLogId: (id: number) => void
}

/** Task list progress: WebSocket primary, HTTP poll fallback + backup while WS is open. */
export function createTaskListTransport(options: TaskListTransportOptions) {
  const { onTasksList } = options

  let pollingTimer: number | null = null
  let wsBackupPollTimer: number | null = null
  let wsSocket: WebSocket | null = null
  let wsFallbackTimer: number | null = null
  let wsHeartbeatTimer: number | null = null
  let wsUsePollingFallback = false
  let consumers = 0
  let wsAllowReconnect = true

  async function pollTasks() {
    if (!shouldPoll()) return
    try {
      const { data } = await listTasks()
      onTasksList(data)
    } catch (e) {
      console.error('Error polling tasks:', e)
    }
  }

  function startWsHeartbeat() {
    if (wsHeartbeatTimer) return
    wsHeartbeatTimer = window.setInterval(() => {
      if (wsSocket?.readyState === WebSocket.OPEN) {
        wsSocket.send('ping')
      }
    }, TASK_WS_HEARTBEAT_MS)
  }

  function stopWsHeartbeat() {
    if (wsHeartbeatTimer) {
      window.clearInterval(wsHeartbeatTimer)
      wsHeartbeatTimer = null
    }
  }

  function startWsBackupPoll() {
    if (wsBackupPollTimer) return
    void pollTasks()
    wsBackupPollTimer = window.setInterval(() => {
      void pollTasks()
    }, TASK_WS_BACKUP_POLL_MS)
  }

  function stopWsBackupPoll() {
    if (wsBackupPollTimer) {
      window.clearInterval(wsBackupPollTimer)
      wsBackupPollTimer = null
    }
  }

  function startPollingFallback() {
    if (pollingTimer) return
    pollTasks()
    pollingTimer = window.setInterval(pollTasks, TASK_POLL_INTERVAL_MS)
  }

  function disconnectWebSocket() {
    if (wsFallbackTimer) {
      window.clearTimeout(wsFallbackTimer)
      wsFallbackTimer = null
    }
    stopWsHeartbeat()
    stopWsBackupPoll()
    if (wsSocket) {
      wsSocket.close()
      wsSocket = null
    }
  }

  function connectWebSocket() {
    if (wsSocket || wsUsePollingFallback) return
    try {
      const socket = new WebSocket(buildTasksWebSocketUrl())
      wsSocket = socket
      socket.onopen = () => {
        const token = window.localStorage.getItem('novel-agent-access-token')
        if (token) socket.send(JSON.stringify({ type: 'auth', token }))
        socket.send('ping')
        startWsHeartbeat()
        if (pollingTimer) {
          window.clearInterval(pollingTimer)
          pollingTimer = null
        }
        startWsBackupPoll()
      }
      socket.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data)
          if (Array.isArray(payload)) {
            onTasksList(payload)
          } else if (payload && (payload.type === 'progress' || payload.type === 'log')) {
            options.onProgressMessage?.(payload)
          }
        } catch {
          /* ignore malformed */
        }
      }
      socket.onerror = () => {
        wsUsePollingFallback = true
        stopWsHeartbeat()
        stopWsBackupPoll()
        socket.close()
        wsSocket = null
        startPollingFallback()
      }
      socket.onclose = () => {
        wsSocket = null
        stopWsHeartbeat()
        stopWsBackupPoll()
        if (!wsUsePollingFallback && wsAllowReconnect && consumers > 0) {
          wsFallbackTimer = window.setTimeout(connectWebSocket, TASK_WS_RECONNECT_MS)
        }
      }
    } catch {
      wsUsePollingFallback = true
      startPollingFallback()
    }
  }

  function start() {
    consumers += 1
    wsAllowReconnect = true
    void pollTasks()
    connectWebSocket()
    if (wsUsePollingFallback) {
      startPollingFallback()
    } else if (wsSocket?.readyState === WebSocket.OPEN) {
      startWsBackupPoll()
    }
  }

  function stop() {
    if (consumers <= 0) return
    consumers -= 1
    if (consumers > 0) return
    wsAllowReconnect = false
    disconnectWebSocket()
    if (pollingTimer) {
      window.clearInterval(pollingTimer)
      pollingTimer = null
    }
  }

  async function refresh() {
    try {
      const { data } = await listTasks()
      onTasksList(data)
    } catch (e) {
      console.error('Error refreshing tasks:', e)
    }
  }

  return { start, stop, refresh }
}

/** Runtime log tail polling with ref-counted consumers (shared 3s interval). */
export function createRuntimeLogTransport(options: RuntimeLogTransportOptions) {
  const { onRuntimeLog, getLastLogId, setLastLogId } = options

  let timer: number | null = null
  let consumers = 0

  async function poll() {
    if (!shouldPoll()) return
    try {
      const { data } = await getRuntimeLogs(getLastLogId(), 200)
      for (const row of data.logs || []) {
        onRuntimeLog(row)
      }
      if (data.last_id) {
        setLastLogId(Math.max(getLastLogId(), data.last_id))
      }
    } catch {
      /* optional when backend busy */
    }
  }

  function start() {
    consumers += 1
    if (timer) return
    poll()
    timer = window.setInterval(poll, RUNTIME_LOG_POLL_INTERVAL_MS)
  }

  function stop() {
    if (consumers <= 0) return
    consumers -= 1
    if (consumers > 0) return
    if (timer) {
      window.clearInterval(timer)
      timer = null
    }
  }

  return { start, stop }
}
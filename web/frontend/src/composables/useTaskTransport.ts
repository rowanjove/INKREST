/** Shared task progress transport timings and WebSocket URL helpers. */

export const TASK_POLL_INTERVAL_MS = 3000
export const TASK_WS_BACKUP_POLL_MS = 8000
export const TASK_WS_HEARTBEAT_MS = 45000
export const TASK_WS_RECONNECT_MS = 5000
export const RUNTIME_LOG_POLL_INTERVAL_MS = 3000

export function isTauriClient(): boolean {
  if (typeof window === 'undefined') return false
  return (
    (window as any).__TAURI_METADATA__ !== undefined ||
    (window as any).__TAURI_INTERNALS__ !== undefined ||
    window.location.protocol === 'tauri:' ||
    window.location.hostname.includes('tauri')
  )
}

export function buildTasksWebSocketUrl(): string {
  if (isTauriClient()) return 'ws://127.0.0.1:8000/ws/tasks'
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/tasks`
}
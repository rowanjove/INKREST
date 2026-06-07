import { shouldPoll } from './pollingGate'

type PollFn = () => void | Promise<void>

interface PollEntry {
  intervalMs: number
  fn: PollFn
  subscribers: number
  timerId: number | null
  lastRunAt: number
}

const HUB_TICK_MS = 1000
const entries = new Map<string, PollEntry>()
let hubTimer: number | null = null

function runDue(entry: PollEntry, now: number) {
  if (!shouldPoll()) return
  if (now - entry.lastRunAt < entry.intervalMs) return
  entry.lastRunAt = now
  void entry.fn()
}

function hubTick() {
  const now = Date.now()
  for (const entry of entries.values()) {
    if (entry.subscribers > 0) {
      runDue(entry, now)
    }
  }
}

function ensureHubTimer() {
  if (hubTimer != null) return
  hubTimer = window.setInterval(hubTick, HUB_TICK_MS)
}

function stopHubTimerIfIdle() {
  const active = [...entries.values()].some((e) => e.subscribers > 0)
  if (!active && hubTimer != null) {
    window.clearInterval(hubTimer)
    hubTimer = null
  }
}

export function subscribePolling(key: string, fn: PollFn, intervalMs: number) {
  let entry = entries.get(key)
  if (!entry) {
    entry = {
      intervalMs,
      fn,
      subscribers: 0,
      timerId: null,
      lastRunAt: 0,
    }
    entries.set(key, entry)
  } else {
    entry.fn = fn
    if (intervalMs < entry.intervalMs) {
      entry.intervalMs = intervalMs
    }
  }
  entry.subscribers += 1
  ensureHubTimer()
  if (shouldPoll()) {
    entry.lastRunAt = 0
    void entry.fn()
  }
}

export function unsubscribePolling(key: string) {
  const entry = entries.get(key)
  if (!entry) return
  entry.subscribers = Math.max(0, entry.subscribers - 1)
  if (entry.subscribers === 0) {
    stopHubTimerIfIdle()
  }
}

export function updatePollingInterval(key: string, intervalMs: number) {
  const entry = entries.get(key)
  if (!entry) return
  entry.intervalMs = intervalMs
}
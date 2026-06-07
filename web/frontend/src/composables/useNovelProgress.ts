import { onMounted, onUnmounted, ref } from 'vue'
import { getNovelProgressSummary } from '../api'
import { shouldPoll } from '../utils/pollingGate'
import { subscribePolling, unsubscribePolling, updatePollingInterval } from '../utils/pollingHub'

export interface NovelProgressSnapshot {
  authoritative_completed: number
  library_indexed: number
  disk_chapters_with_final: number
  disk_pipeline_complete: number
  pending_total: number
  pending_retry_count: number
  pending_gate_count: number
  batch_status: string
  batch_paused: boolean
  pause_reason: string
  last_arc_id: string
  last_chapter_id: string
  fail_streak: number
  remaining_chapters: number
  progress_note: string
}

const POLL_KEY = 'novel-progress'
const snapshot = ref<NovelProgressSnapshot | null>(null)
const loading = ref(false)
let subscriberCount = 0
let pollIntervalMs = 0

function normalize(data: Record<string, unknown>): NovelProgressSnapshot {
  return {
    authoritative_completed: Number(data.authoritative_completed ?? 0),
    library_indexed: Number(data.library_indexed ?? 0),
    disk_chapters_with_final: Number(data.disk_chapters_with_final ?? 0),
    disk_pipeline_complete: Number(data.disk_pipeline_complete ?? 0),
    pending_total: Number(data.pending_total ?? 0),
    pending_retry_count: Number(data.pending_retry_count ?? 0),
    pending_gate_count: Number(data.pending_gate_count ?? 0),
    batch_status: String(data.batch_status ?? 'idle'),
    batch_paused: Boolean(data.batch_paused),
    pause_reason: String(data.pause_reason ?? ''),
    last_arc_id: String(data.last_arc_id ?? ''),
    last_chapter_id: String(data.last_chapter_id ?? ''),
    fail_streak: Number(data.fail_streak ?? 0),
    remaining_chapters: Number(data.remaining_chapters ?? 0),
    progress_note: String(data.progress_note ?? ''),
  }
}

export async function refreshNovelProgress() {
  if (!shouldPoll()) return
  loading.value = true
  try {
    const { data } = await getNovelProgressSummary()
    snapshot.value = normalize(data || {})
  } catch {
    /* 保留上次快照 */
  } finally {
    loading.value = false
  }
}

function beginPolling(intervalMs: number) {
  if (intervalMs <= 0) return
  pollIntervalMs = intervalMs
  subscribePolling(POLL_KEY, refreshNovelProgress, pollIntervalMs)
}

function tightenPolling(intervalMs: number) {
  if (intervalMs <= 0 || pollIntervalMs === 0 || intervalMs >= pollIntervalMs) return
  pollIntervalMs = intervalMs
  updatePollingInterval(POLL_KEY, intervalMs)
}

export function useNovelProgress(options?: { pollMs?: number }) {
  const pollMs = options?.pollMs ?? 0

  onMounted(() => {
    subscriberCount += 1
    if (subscriberCount === 1) {
      void refreshNovelProgress()
      beginPolling(pollMs)
    } else {
      tightenPolling(pollMs)
    }
  })

  onUnmounted(() => {
    subscriberCount = Math.max(0, subscriberCount - 1)
    if (subscriberCount === 0 && pollIntervalMs > 0) {
      unsubscribePolling(POLL_KEY)
      pollIntervalMs = 0
    }
  })

  return {
    snapshot,
    loading,
    refresh: refreshNovelProgress,
  }
}
import type { ChapterProgress } from '../entities/project/projectSnapshot'
import type { OutlineQueueStatus } from '../entities/outline/outlineQueueStatus'

export type OverviewTone = 'neutral' | 'success' | 'warning' | 'danger'

function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export function progressHasSourceMismatch(progress: ChapterProgress | null | undefined): boolean {
  if (!progress) return false
  const authoritative = numberOrNull(progress.authoritative_completed)
  if (authoritative === null) return false
  return [progress.library_indexed, progress.disk_chapters_with_final]
    .map(numberOrNull)
    .some((value) => value !== null && value !== authoritative)
}

export function progressTone(progress: ChapterProgress | null | undefined): OverviewTone {
  if (!progress) return 'neutral'
  if (Number(progress.pending_gate_count || 0) > 0) return 'danger'
  if (Boolean(progress.batch_paused) || Number(progress.pending_total || 0) > 0) return 'warning'
  if (progressHasSourceMismatch(progress)) return 'warning'
  return 'success'
}

export function queueTone(status: OutlineQueueStatus | null | undefined): OverviewTone {
  if (!status) return 'neutral'
  if (status.arc_queue_stale?.stale) return 'warning'
  const pending = numberOrNull(status.pending_briefs)
  const target = numberOrNull(status.target_chapters)
  const lastWritten = numberOrNull(status.last_written_chapter)
  if (pending === 0 && target !== null && lastWritten !== null && lastWritten < target) return 'warning'
  return pending && pending > 0 ? 'success' : 'neutral'
}


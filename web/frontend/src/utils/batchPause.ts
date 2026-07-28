/** 全书批量暂停原因 — 与 arc_queue / novel_batch_progress 对齐 */

export const REPAIR_BEFORE_RESUME_REASONS = new Set([
  'circuit_breaker',
  'quality_blocked',
  'batch_skip_limit',
  'chapter_retry_exhausted',
])

export const BATCH_PAUSE_LABELS: Record<string, string> = {
  circuit_breaker: '质量熔断',
  quality_blocked: '门禁阻断',
  batch_skip_limit: '跳章保护',
  chapter_retry_exhausted: '单章重试耗尽',
  paused: '已暂停',
}

export function needsRepairBeforeResume(pauseReason?: string | null): boolean {
  const reason = String(pauseReason || 'circuit_breaker')
  return REPAIR_BEFORE_RESUME_REASONS.has(reason)
}

export function formatBatchPauseReason(pauseReason?: string | null): string {
  const reason = String(pauseReason || 'circuit_breaker')
  return BATCH_PAUSE_LABELS[reason] || reason
}
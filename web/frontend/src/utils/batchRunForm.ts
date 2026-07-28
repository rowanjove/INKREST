export type BatchRunForm = {
  target_chapters: number
  autopilot: boolean
}

export type BatchRunPhase = 'idle' | 'opening' | 'syncing_queue' | 'submitting_continue'

export function batchFormStorageKey(projectId: string): string {
  return `inkrest_batch_form_${projectId}`
}

export function loadSavedBatchForm(projectId: string): BatchRunForm | null {
  if (!projectId) return null
  try {
    const raw = localStorage.getItem(batchFormStorageKey(projectId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<BatchRunForm>
    const target = Number(parsed.target_chapters)
    if (!Number.isFinite(target) || target < 1) return null
    return {
      target_chapters: Math.floor(target),
      autopilot: Boolean(parsed.autopilot),
    }
  } catch {
    return null
  }
}

export function saveBatchForm(projectId: string, form: BatchRunForm): void {
  if (!projectId) return
  try {
    localStorage.setItem(batchFormStorageKey(projectId), JSON.stringify(form))
  } catch {
    /* quota / private mode */
  }
}

export function applyBatchFormDefaults(
  workScale: string,
  maxAvailableChapters: number,
): BatchRunForm {
  const cap = Math.max(0, maxAvailableChapters)
  let autopilot = workScale !== 'micro'
  let target_chapters = Math.min(5, cap)

  if (workScale === 'long') {
    target_chapters = Math.min(10, cap)
  } else if (workScale === 'epic' || workScale === 'infinite') {
    target_chapters = Math.min(10, cap)
    autopilot = true
  } else if (workScale === 'micro' || workScale === 'short') {
    target_chapters = cap
    autopilot = false
  }
  if (autopilot && cap > 0) {
    target_chapters = cap
  }
  return { target_chapters: Math.max(1, target_chapters || 1), autopilot }
}

export function mergeBatchForm(
  defaults: BatchRunForm,
  saved: BatchRunForm | null,
  maxAvailableChapters: number,
): BatchRunForm {
  const cap = Math.max(1, maxAvailableChapters || 1)
  if (!saved) {
    return {
      target_chapters: Math.min(defaults.target_chapters, cap),
      autopilot: defaults.autopilot,
    }
  }
  return {
    target_chapters: Math.min(Math.max(1, saved.target_chapters), cap),
    autopilot: saved.autopilot,
  }
}

export function cancelBatchRunMessage(phase: BatchRunPhase, continueSubmitted: boolean): string {
  if (phase === 'opening') return '已取消加载开书状态'
  if (phase === 'syncing_queue') return '已取消同步卷队列'
  if (phase === 'submitting_continue' || continueSubmitted) {
    return '已发送取消请求；任务可能仍在后台运行，请到日志中心查看'
  }
  return '已取消连写启动'
}

export function computeRoundProgress(opts: {
  roundTarget: number
  startChapterCount: number
  currentChapterCount: number
}): { target: number; written: number; label: string } {
  const target = Math.max(0, opts.roundTarget)
  const written = Math.max(0, opts.currentChapterCount - opts.startChapterCount)
  const label =
    target > 0
      ? `本轮上限 ${target} 章 · 已写 ${Math.min(written, target)} 章`
      : `已写 ${written} 章`
  return { target, written, label }
}
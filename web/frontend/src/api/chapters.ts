import api from './client'

export const runChapter = (data: { chapter_id: string; goal: string; dry_run?: boolean }) =>
  api.post('/chapters/run', data)

export const listTasks = () =>
  api.get('/chapters/tasks')

export const abortTask = (taskId: string) =>
  api.post(`/chapters/tasks/${taskId}/abort`)

export const getArcProgress = () =>
  api.get('/novel/arc-progress')

export const getNovelBatchStatus = () =>
  api.get('/novel/batch-status')

export const getNovelProgressSummary = () => api.get('/novel/progress-summary')

export const getNovelReadiness = () => api.get('/novel/readiness')

export const rerunChapterGate = (chapterId: string) =>
  api.post(`/chapters/${chapterId}/rerun-gate`)

export const setChapterExternalReview = (
  chapterId: string,
  data: { status: 'none' | 'pending_external' | 'external_passed'; note?: string },
) => api.patch(`/chapters/${chapterId}/external-review`, data)

export const continueNovel = (
  data?: {
    resume?: boolean
    max_chapters?: number
    dry_run?: boolean
    autopilot?: boolean
    full_book?: boolean
    chapters_per_round?: number
    max_rounds?: number
    force_resume?: boolean
  },
  opts?: { signal?: AbortSignal },
) =>
  api.post('/novel/continue', data || {}, { signal: opts?.signal })

export const ensureNovelQueue = (opts?: { timeout?: number; signal?: AbortSignal }) =>
  api.post('/novel/ensure-queue', undefined, {
    timeout: opts?.timeout ?? 600_000,
    signal: opts?.signal,
  })

export const rebuildEmbeddingIndex = () =>
  api.post('/config/embedding/rebuild-index')

export const getChapterCount = (sync = true) =>
  api.get<{ total: number }>('/chapters/count', { params: { sync } })

export const listChapters = (params?: {
  offset?: number
  limit?: number
  sync?: boolean
  include_gaps?: boolean
}) =>
  api.get('/chapters', { params })

export const getChapter = (chapterId: string) =>
  api.get(`/chapters/${chapterId}`)

export const rewriteChapter = (chapterId: string) =>
  api.post(`/chapters/${chapterId}/rewrite`)

export const rewriteBatchChapters = (chapterIds: string[], dryRun = false) =>
  api.post('/chapters/rewrite-batch', { chapter_ids: chapterIds, dry_run: dryRun })

export const resumeChapterAudit = (chapterId: string) =>
  api.post(`/chapters/${chapterId}/resume-audit`)

export const generateOutline = (data: {
  theme: string
  genre?: string
  target_chapters?: number
  scale?: string
  scale_label?: string
  special_requirements?: string
  overwrite?: boolean
}) =>
  api.post('/novel/plan', data)

export const analyzeNovelIntro = (text: string) =>
  api.post('/novel/analyze-intro', { text })

export const updateOutline = (data: Record<string, any>) =>
  api.put('/outline', data)


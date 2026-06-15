import api from './client'

export type TaskQueueSnapshot = {
  scale?: string
  max_concurrent_chapters: number
  max_scene_workers?: number
  active_task_count: number
  running_chapters: string[]
  novel_batch_task_id?: string | null
}

export const runChapter = (data: { chapter_id: string; goal: string; dry_run?: boolean }) =>
  api.post('/chapters/run', data)

export const runBatchChapters = (data: { chapters: Array<{ chapter_id: string; goal: string }>; dry_run?: boolean }) =>
  api.post('/chapters/run-batch', data)

export const getTask = (taskId: string) =>
  api.get(`/chapters/tasks/${taskId}`)

export const listTasks = () =>
  api.get('/chapters/tasks')

export const getTaskQueue = () =>
  api.get<TaskQueueSnapshot>('/chapters/tasks/queue')

export const abortTask = (taskId: string) =>
  api.post(`/chapters/tasks/${taskId}/abort`)

export const getArcProgress = () =>
  api.get('/novel/arc-progress')

export const getNovelBatchStatus = () =>
  api.get('/novel/batch-status')

export const getCostSummary = () => api.get('/novel/cost-summary')

export const getNovelProgressSummary = () => api.get('/novel/progress-summary')

/** @deprecated 调试/CLI 用。用户连写请用 ensureNovelQueue + continueNovel。 */

export const runNovelArc = (data: {
  arc_id?: string
  arc_ids?: string[]
  start_arc_id?: string
  resume?: boolean
  max_chapters?: number
  dry_run?: boolean
}) =>
  api.post('/novel/run-arc', data)

export const getNovelReadiness = () => api.get('/novel/readiness')

export const getAutopilotRounds = (limit = 50, offset = 0) =>
  api.get('/novel/autopilot-rounds', { params: { limit, offset } })

export const rerunChapterGate = (chapterId: string) =>
  api.post(`/chapters/${chapterId}/rerun-gate`)

export const setChapterExternalReview = (
  chapterId: string,
  data: { status: 'none' | 'pending_external' | 'external_passed'; note?: string },
) => api.patch(`/chapters/${chapterId}/external-review`, data)

export const exportChaptersTrial = (data: { chapter_ids?: string[]; include_titles?: boolean }) =>
  api.post('/chapters/export-trial', data)

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

export const deleteChapter = (chapterId: string) =>
  api.delete(`/chapters/${chapterId}`)

export const updateChapter = (chapterId: string, data: { title?: string; final_text: string }) =>
  api.put(`/chapters/${chapterId}`, data)

export const createChapter = (data: { chapter_id: string; title: string }) =>
  api.post('/chapters', data)

export const suggestChapterGoal = (chapterId: string) =>
  api.get(`/chapters/${chapterId}/suggest-goal`)

export const listSnapshots = (chapterId: string) =>
  api.get(`/chapters/${chapterId}/snapshots`)

export const createSnapshot = (chapterId: string, data: { title: string }) =>
  api.post(`/chapters/${chapterId}/snapshots`, data)

export const rollbackSnapshot = (chapterId: string, timestamp: number) =>
  api.post(`/chapters/${chapterId}/snapshots/${timestamp}/rollback`)

// ---- Chapter Versions & Branch Writing ----

export const listVersions = (chapterId: string) =>
  api.get(`/chapters/${chapterId}/versions`)

export const createVersion = (chapterId: string, data: { version_name: string; note?: string; copy_from_active?: boolean }) =>
  api.post(`/chapters/${chapterId}/versions`, data)

export const updateVersion = (versionId: string, data: { version_name?: string; note?: string; content?: string }) =>
  api.put(`/chapters/versions/${versionId}`, data)

export const deleteVersion = (versionId: string) =>
  api.delete(`/chapters/versions/${versionId}`)

export const activateVersion = (chapterId: string, versionId: string) =>
  api.post(`/chapters/${chapterId}/versions/${versionId}/activate`)

export const compareVersions = (chapterId: string, data: { version_id_a: string; version_id_b: string }) =>
  api.post(`/chapters/${chapterId}/versions/compare`, data)

export const getScrapbook = (params?: { query?: string; chapter_id?: string }) =>
  api.get('/scrapbook', { params })

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

/** @deprecated 冷启动全书规划，跳过开书清单。用户请用工作台「自动生成章节」。 */

export const runNovel = (data: {
  theme: string
  genre?: string
  target_chapters?: number
  scale?: string
  scale_label?: string
  special_requirements?: string
  dry_run?: boolean
}) =>
  api.post('/novel/run', data)

import axios from 'axios'

const isTauri = typeof window !== 'undefined' && (
  (window as any).__TAURI_METADATA__ !== undefined ||
  (window as any).__TAURI_INTERNALS__ !== undefined ||
  window.location.protocol === 'tauri:' ||
  window.location.hostname.includes('tauri')
);

const getBaseURL = () => {
  if (isTauri) {
    return 'http://127.0.0.1:8000/api';
  }
  return '/api';
};

const api = axios.create({ baseURL: getBaseURL() })

export const apiErrorMessage = (error: any, fallback = '操作失败') => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => item?.msg || item?.message || JSON.stringify(item))
      .filter(Boolean)
    if (parts.length) return parts.join('；')
  }
  if (detail && typeof detail === 'object') {
    const hint = detail.hint || detail.failure_hint
    const msg = detail.detail || detail.message
    if (hint && msg && hint !== msg) return `${msg}（${hint}）`
    if (hint) return String(hint)
    if (msg) return String(msg)
    if (detail.code) return `[${detail.code}] ${msg || hint || '请求失败'}`
    return JSON.stringify(detail)
  }
  if (error?.response?.status) return fallback
  if (typeof error?.message === 'string' && /^Request failed with status code \d+/.test(error.message)) {
    return fallback
  }
  return error?.message || fallback
}

export async function bootstrapLocalAccessToken(): Promise<void> {
  if (typeof window === 'undefined') return
  if (window.localStorage.getItem('novel-agent-access-token')) return
  try {
    const base = getBaseURL().replace(/\/api\/?$/, '')
    const response = await fetch(`${base}/api/auth/local-setup`)
    if (!response.ok) return
    const data = await response.json()
    if (data?.token) {
      window.localStorage.setItem('novel-agent-access-token', data.token)
    }
  } catch {
    // Server may not expose local token (remote bind); user can paste token manually.
  }
}

api.interceptors.request.use((config) => {
  const token = window.localStorage.getItem('novel-agent-access-token')
  if (token) config.headers['X-Novel-Agent-Token'] = token
  return config
})
api.interceptors.response.use(undefined, async (error) => {
  const config = error.config as typeof error.config & { _accessTokenRetried?: boolean }
  if (error.response?.status === 401 && config && !config._accessTokenRetried) {
    const token = window.prompt('请输入栖墨远程访问令牌')
    if (token) {
      window.localStorage.setItem('novel-agent-access-token', token)
      config._accessTokenRetried = true
      config.headers['X-Novel-Agent-Token'] = token
      return api.request(config)
    }
  }
  const message = apiErrorMessage(error, error.message)
  if (message) error.message = message
  return Promise.reject(error)
})

// ---- Chapters ----

export const runChapter = (data: { chapter_id: string; goal: string; dry_run?: boolean }) =>
  api.post('/chapters/run', data)

export const runBatchChapters = (data: { chapters: Array<{ chapter_id: string; goal: string }>; dry_run?: boolean }) =>
  api.post('/chapters/run-batch', data)

export const getTask = (taskId: string) =>
  api.get(`/chapters/tasks/${taskId}`)

export const listTasks = () =>
  api.get('/chapters/tasks')

export const getSystemReadiness = () =>
  api.get('/system/readiness')

export const abortTask = (taskId: string) =>
  api.post(`/chapters/tasks/${taskId}/abort`)

export const getArcProgress = () =>
  api.get('/novel/arc-progress')

export const getNovelBatchStatus = () =>
  api.get('/novel/batch-status')

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

export const getNovelProgressSummary = () => api.get('/novel/progress-summary')

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

// ---- State ----

export const getState = (params?: { sync?: boolean }) =>
  api.get('/state', { params })

export const getTimeline = () =>
  api.get('/state/timeline')

export const searchEvents = (query: string, limit = 20) =>
  api.get('/events', { params: { query, limit } })

// ---- Assets ----

export const listAssets = () =>
  api.get('/assets')

export const getAsset = (name: string) =>
  api.get(`/assets/${name}`)

export const updateAsset = (name: string, content: string) =>
  api.put(`/assets/${name}`, { content })

export const createAsset = (data: { name: string; label?: string; extension?: string; content?: string }) =>
  api.post('/assets', data)

export const generateAsset = (data: {
  name: string
  label?: string
  asset_type?: string
  count?: number
  attributes?: string[]
  parameters?: Record<string, unknown>
  instructions?: string
}) =>
  api.post('/assets/generate', data)

export const importToTerminology = (data: { names: string[] }) =>
  api.post('/assets/import-to-terminology', data)

export const deleteAsset = (name: string) =>
  api.delete(`/assets/${name}`)


// ---- Config ----

export const getConfig = () =>
  api.get('/config')

export const updateConfig = (data: Record<string, unknown>) =>
  api.put('/config', data)

// ---- Prompts ----

export const listPrompts = () =>
  api.get('/prompts')

export const getPrompt = (role: string) =>
  api.get(`/prompts/${role}`)

export const updatePrompt = (role: string, content: string) =>
  api.put(`/prompts/${role}`, { content })

export const resetPrompt = (role: string) =>
  api.post(`/prompts/${role}/reset`)

// ---- Database ----

export const clearDatabase = () =>
  api.post('/database/clear', { confirm: true })

// ---- Dashboard ----

export const getDashboard = () =>
  api.get('/dashboard')

// ---- Outline ----

export const getOutline = () =>
  api.get('/outline')

// ---- Longform Control ----

export const getNarrativeDebt = (currentChapter = '') =>
  api.get('/control/narrative-debt', { params: { current_chapter: currentChapter } })

export const getCalibrationReport = () =>
  api.get('/control/calibration')

export const getScaleProfile = () =>
  api.get('/control/scale-profile')

export const getPipelineAlerts = () =>
  api.get('/pipeline-alerts')

export const dismissPipelineAlert = (chapterId: string) =>
  api.post(`/pipeline-alerts/${chapterId}/dismiss`)

export const collectDebt = (data: { debt_type: string; debt_id: string; priority?: number }) =>
  api.post('/control/narrative-debt/collect', data)

export const getCharacterRelations = () =>
  api.get('/control/character-relations')

export const saveCharacterRelation = (data: {
  source_char: string;
  target_char: string;
  relation_type: string;
  intensity: number;
  since_chapter?: number;
  last_updated?: number;
  description?: string;
}) =>
  api.post('/control/character-relations', data)

export const deleteCharacterRelation = (relationId: number) =>
  api.delete(`/control/character-relations/${relationId}`)

// ---- Export ----

export const exportNovel = (params: { format: string; title?: string; chapter_ids?: string; project_id?: string }) =>
  api.post('/export', null, { params, responseType: 'blob' })

export const exportProjectZip = (pid: string) =>
  api.get(`/projects/${pid}/export-zip`, { responseType: 'blob' })

export const importProjectZip = (formData: FormData) =>
  api.post('/projects/import-zip', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

// ---- Projects ----

export const listProjects = () =>
  api.get('/projects')

export const getCurrentProject = () =>
  api.get('/projects/current')

export const createProject = (data: {
  name: string
  description?: string
  preset_id?: string
  genre?: string
  channel?: string
  target_chapters?: number
  scale?: string
  scale_label?: string
  target_chars_per_chapter?: number[]
  scale_profile?: Record<string, unknown>
  outline?: Record<string, unknown>
  preset_channel?: string
  preset_theme?: string
  preset_mechanisms?: string[]
  preset_cool_points?: string[]
}) =>
  api.post('/projects', data)

export const deleteProject = (id: string) =>
  api.delete(`/projects/${id}`)

export const switchProject = (id: string) =>
  api.post(`/projects/${id}/switch`)

export const pinProject = (id: string, pinned: boolean) =>
  api.put(`/projects/${id}/pin`, { pinned })

// ---- Novel Chat (AI-guided creation) ----

export const novelChatStep = (data: {
  step: number
  user_input: string
  context: Record<string, unknown>
}) =>
  api.post('/novel/chat', data)

export const novelChatIntro = (step: number) =>
  api.get(`/novel/chat/intro/${step}`)

export const generateChapterPlan = (data: {
  start_chapter?: number
  count?: number
  instructions?: string
}) =>
  api.post('/novel/chapter-plan', data)

// ---- Presets ----

export const listPresets = (params?: { channel?: string }) =>
  api.get('/presets', { params })

export const getPreset = (id: string) =>
  api.get(`/presets/${id}`)

export const createPreset = (data: { name: string; channel: string; category: string; subcategory?: string; tags?: string[]; description?: string; guide: string }) =>
  api.post('/presets', data)

export const deletePreset = (id: string) =>
  api.delete(`/presets/${id}`)

// ---- Composable Preset Components ----

export const listComponents = (type: string, params?: { channel?: string }) =>
  api.get('/presets/components', { params: { type, ...params } })

export const getComponent = (type: string, id: string) =>
  api.get(`/presets/components/${type}/${id}`)

export const composePreset = (data: {
  channel: string
  theme: string
  mechanisms?: string[]
  cool_points?: string[]
  project_id?: string
}) =>
  api.post('/presets/compose', data)

// ---- Models ----

export const listModels = () =>
  api.get('/models')

export const getModelSlots = () =>
  api.get<{ daily: string; reasoning: string; backup: string[] }>('/models/slots')

export const setModelSlot = (modelId: string, slot: '' | 'daily' | 'reasoning' | 'backup') =>
  api.patch(`/models/${modelId}/slot`, { slot })

export const saveModel = (data: Record<string, unknown>) =>
  api.post('/models', data)

export const deleteModel = (id: string) =>
  api.delete(`/models/${id}`)

export const testModel = (data: Record<string, unknown>) =>
  api.post('/models/test', data)

export const getEmbeddingStatus = () =>
  api.get('/config/embedding/status')

export const getArcQueueStale = () =>
  api.get('/outline/arc-queue-stale')

export const markArcQueueSynced = () =>
  api.post('/outline/arc-queue-synced')

export const getOutlineQueueStatus = () =>
  api.get('/outline/queue-status')

export const startSetupLocal = () =>
  api.post('/config/embedding/setup-local')

export const getSetupLocalStatus = () =>
  api.get('/config/embedding/setup-status')


// ---- Plugins ----

export const listPlugins = () =>
  api.get('/plugins')

export const listUntrustedPlugins = () =>
  api.get('/plugins/untrusted')

export const trustPlugin = (name: string) =>
  api.post(`/plugins/${name}/trust`)

export const getPlugin = (name: string) =>
  api.get(`/plugins/${name}`)

export const togglePlugin = (name: string, enabled: boolean) =>
  api.put(`/plugins/${name}/toggle`, { enabled })

export const updatePluginConfig = (name: string, config: Record<string, any>) =>
  api.put(`/plugins/${name}/config`, { config })

export const reloadPlugins = () =>
  api.post('/plugins/reload')

export const installPluginZip = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/plugins/install', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const deletePlugin = (name: string) =>
  api.delete(`/plugins/${name}`)

// ---- Runtime / LLM Logs ----
export const getRuntimeLogs = (sinceId = 0, limit = 200) =>
  api.get('/runtime-logs', { params: { since_id: sinceId, limit } })

export const clearRuntimeLogs = () =>
  api.delete('/runtime-logs')

export const getLLMLogs = () =>
  api.get('/llm-logs')

// ---- Assistant ----
export const getAssistantContext = () =>
  api.get('/assistant/context')

export const sendAssistantChat = (data: { message: string; history: any[]; context?: any }) =>
  api.post('/assistant/chat', data)

export const getAssistantDiagnose = (ignoredTaskIds?: string[]) =>
  api.get('/assistant/diagnose', { params: { ignored_task_ids: ignoredTaskIds?.join(',') } })

export const fixAssistantIssue = (data: { fix_type: string; payload?: any }) =>
  api.post('/assistant/fix', data)

export const inlineRewrite = (data: { text: string; instruction: string; chapter_id?: string; goal?: string }) =>
  api.post('/assistant/inline-rewrite', data)

export const inlineExpand = (data: { before_text: string; chapter_id?: string; goal?: string }) =>
  api.post('/assistant/inline-expand', data)

export const extractSyncAssets = (data: { chapter_text: string }) =>
  api.post('/assets/extract-sync', data)

// ---- Project Cover & Description Rewrite ----
export const getProjectCoverUrl = (pid: string) => `/api/projects/${pid}/cover`

export const suggestCoverPrompt = (pid: string) =>
  api.post(`/projects/${pid}/suggest-cover-prompt`)

export const generateCover = (pid: string, data: { model_id: string; prompt: string }) =>
  api.post(`/projects/${pid}/generate-cover`, data)

export const saveCover = (pid: string, coverBase64: string) =>
  api.post(`/projects/${pid}/save-cover`, { cover: coverBase64 })

export const rewriteDescription = (pid: string, data: { old_description: string; style: string; user_preference?: string }) =>
  api.post(`/projects/${pid}/rewrite-description`, data)

export const updateDescription = (pid: string, description: string) =>
  api.post(`/projects/${pid}/update-description`, { description })

// ---- Platform Profiles & Reader Feedback ----
export const listPlatforms = () =>
  api.get('/platforms')

export const getProjectPlatform = (pid: string) =>
  api.get(`/projects/${pid}/platform`)

export const updateProjectPlatform = (pid: string, platform: string) =>
  api.post(`/projects/${pid}/platform`, { platform })

export const saveReaderFeedback = (pid: string, data: { chapter_id: string; bounce_rate: number; retention_rate: number; active_readers: number }) =>
  api.post(`/projects/${pid}/feedback`, data)

export const listReaderFeedback = (pid: string) =>
  api.get(`/projects/${pid}/feedback`)

export const getGoldenCheck = (pid: string) =>
  api.get(`/projects/${pid}/golden-check`)

// ---- Serialization Workbench OS ----
export const getSerialStatus = (pid: string) =>
  api.get(`/projects/${pid}/serial-status`)

export const getProjectComments = (pid: string) =>
  api.get(`/projects/${pid}/comments`)

export const adaptiveRewriteOutline = (pid: string) =>
  api.post(`/projects/${pid}/outline/adaptive-rewrite`)

export const applyAdaptiveOutline = (pid: string, data: { new_chapters: any[] }) =>
  api.post(`/projects/${pid}/outline/apply-adaptive`, data)

export const exportSerial = (pid: string, format: string = 'zip') =>
  api.get(`/projects/${pid}/export-serial`, { params: { format }, responseType: 'blob' })

export const getProjectStateCandidates = (pid: string) =>
  api.get(`/projects/${pid}/state-candidates`)

export const approveAllProjectCandidates = (pid: string) =>
  api.post(`/projects/${pid}/state-candidates/approve-all`)

export const actionOnStateCandidate = (candidateId: string, action: 'accept' | 'reject') =>
  api.post(`/chapters/state-candidates/${candidateId}/action`, { action })

export const sendPetDebugLog = (payload: any) =>
  api.post('/pet/debug-log', payload)

// ---- Agent bridge (CLI / MCP / external AI) ----

export const getAgentBridgeSettings = () => api.get('/agent/settings')

export const updateAgentBridgeSettings = (data: {
  mcp_mode?: 'auto' | 'offline' | 'http'
  api_url_override?: string
  show_integration_hints?: boolean
}) => api.put('/agent/settings', data)

export const getAgentSnapshot = (params?: { project_id?: string }) =>
  api.get('/agent/snapshot', { params })

export const getAgentProjects = () => api.get('/agent/projects')

export default api

export { apiErrorMessage, bootstrapLocalAccessToken } from './api/client'
export { default } from './api/client'
export * from './api/factory'
export * from './api/chapters'
export * from './api/projectSnapshot'
export * from './api/publishing'
export * from './api/quality'

import api from './api/client'
import type { PlanningWorkspace } from './entities/planning/planningWorkspace'

export const getPlanningWorkspace = () =>
  api.get<PlanningWorkspace>('/planning/workspace')

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

export const getLongformReadiness = () =>
  api.get('/longform/readiness')

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

export const getPromptManifest = () =>
  api.get('/prompts/manifest')

export const getProseProfile = () =>
  api.get('/prose-profile')

export const getProseProfileVersions = () =>
  api.get('/prose-profile/versions')

export const restoreProseProfile = (revision: number) =>
  api.post('/prose-profile/restore', { revision })

// ---- Outline ----

export const getOutline = () =>
  api.get('/outline')

export const getOutlineRevision = () =>
  api.get<{ revision: number; digest: string }>('/outline/revision')

// ---- Longform Control ----

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
  factory_mode?: string
}) =>
  api.post('/projects', data)

export const deleteProject = (id: string) =>
  api.delete(`/projects/${id}`)

export const switchProject = (id: string) =>
  api.post(`/projects/${id}/switch`)

export const pinProject = (id: string, pinned: boolean) =>
  api.put(`/projects/${id}/pin`, { pinned })

export const renameProject = (id: string, name: string) =>
  api.patch(`/projects/${id}/name`, { name })

export interface ProjectBackupResult {
  path: string
  name: string
  sha256: string
  size_bytes: number
  file_count: number
  created_at: string
}

export const backupProject = (id: string) =>
  api.post<{ status: 'backed_up'; backup: ProjectBackupResult }>(
    `/projects/${id}/backup`,
    { confirmation: `BACKUP ${id}` },
  )

export const resetProjectToV2 = (id: string, confirmation: string) =>
  api.post<{
    status: 'reset'
    backup: ProjectBackupResult
    schema_version: number
    cleared_roots: string[]
  }>(`/projects/${id}/reset-v2`, { confirmation })

// ---- Novel Chat (AI-guided creation) ----

export const novelChatStep = (data: {
  step: number
  user_input: string
  context: Record<string, unknown>
}) =>
  api.post('/novel/chat', data)

export const novelChatIntro = (step: number) =>
  api.get(`/novel/chat/intro/${step}`)

// ---- Composable Preset Components ----

export const listComponents = (type: string, params?: { channel?: string }) =>
  api.get('/presets/components', { params: { type, ...params } })

export const getComponent = (type: string, id: string) =>
  api.get(`/presets/components/${type}/${id}`)

// ---- Models ----

export const getModelReadiness = () =>
  api.get('/models/readiness')

export const listModels = () =>
  api.get('/models')

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

export const fetchPluginNavigation = () =>
  api.get('/plugins/navigation')

export const createPluginViewSession = (
  pluginId: string,
  viewId: string,
  projectId?: string,
  contextRevision = 1,
) =>
  api.post(`/plugins/${pluginId}/views/${viewId}/session`, {
    project_id: projectId,
    context_revision: contextRevision,
  })

export const closePluginViewSession = (pluginId: string, viewId: string, sessionId: string) =>
  api.delete(`/plugins/${pluginId}/views/${viewId}/session/${sessionId}`)

export const fetchPluginViewDocument = (pluginId: string, viewId: string, sessionId: string) =>
  api.get<{ title: string; html: string; has_document: boolean }>(
    `/plugins/${pluginId}/views/${viewId}/document`,
    { params: { session_id: sessionId } },
  )

export const executePluginViewRpc = (
  pluginId: string,
  viewId: string,
  sessionId: string,
  method: string,
  params?: any,
  contextRevision = 1,
) =>
  api.post(`/plugins/${pluginId}/views/${viewId}/rpc`, {
    session_id: sessionId,
    method,
    params,
    context_revision: contextRevision,
  })

export const listUntrustedPlugins = () =>
  api.get('/plugins/untrusted')

export const trustPlugin = (
  name: string,
  digest: string,
  capabilities: string[],
  acknowledgeLocalCode = false,
) =>
  api.post(`/plugins/${name}/trust`, {
    digest,
    capabilities,
    acknowledge_local_code: acknowledgeLocalCode,
  })

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

export const listAssistantSkills = () =>
  api.get<{ skills: Array<{ id: string; name: string; command: string; description?: string; produces_patch?: boolean }> }>('/assistant/skills')

export const listAssistantPatches = (chapterId?: string) =>
  api.get<{ patches: any[] }>('/assistant/patches', { params: chapterId ? { chapter_id: chapterId } : {} })

export const applyAssistantPatch = (patchId: string) =>
  api.post<{ success: boolean; patch: any; new_text?: string }>(`/assistant/patches/${patchId}/apply`)

export const rejectAssistantPatch = (patchId: string) =>
  api.post<{ success: boolean; patch: any }>(`/assistant/patches/${patchId}/reject`)

export const revertAssistantPatch = (patchId: string) =>
  api.post<{ success: boolean; patch: any; reverted_text?: string }>(`/assistant/patches/${patchId}/revert`)

export const listAssistantPreferences = () =>
  api.get<{ preferences: Array<{ id: string; scope: string; preference_type: string; content: string; created_at?: string }> }>('/assistant/preferences')

export const createAssistantPreference = (data: { content: string; preference_type?: string; scope?: string }) =>
  api.post<{ success: boolean; preference: any }>('/assistant/preferences', data)

export const deleteAssistantPreference = (prefId: string) =>
  api.delete<{ success: boolean; deleted_id: string }>(`/assistant/preferences/${prefId}`)

export const previewAssistantContext = (data: {
  message: string
  editor_context?: any
  skill_id?: string
}) =>
  api.post<{
    chips: any[]
    citations: any[]
    budget_breakdown: Record<string, number>
    total_chars: number
    preview_text: string
  }>('/assistant/context/preview', data)

export const listAssistantTools = () =>
  api.get<{
    tools: Array<{
      name: string
      description: string
      permission_level: number
      requires_confirmation: boolean
      parameters_schema?: any
    }>
  }>('/assistant/tools')

export const listAssistantRuns = (limit = 50) =>
  api.get<{ runs: any[] }>('/assistant/runs', { params: { limit } })

export const getAssistantRun = (runId: string) =>
  api.get<{ run: any }>(`/assistant/runs/${runId}`)

export const confirmAssistantRunAction = (runId: string, action: any) =>
  api.post<{
    run_id: string
    reply: string
    status: string
    steps: any[]
    total_elapsed_ms: number
  }>(`/assistant/runs/${runId}/confirm`, { action })

export const listAssistantThreads = (limit = 50) =>
  api.get<{ threads: Array<{ id: string; title: string; created_at: string; updated_at: string }> }>(
    '/assistant/threads',
    { params: { limit } },
  )

export const createAssistantThread = (title = '新对话') =>
  api.post<{ thread: { id: string; title: string; created_at: string; updated_at: string } }>(
    '/assistant/threads',
    { title },
  )

export const listAssistantThreadMessages = (threadId: string, limit = 100) =>
  api.get<{ messages: Array<{ id: string; thread_id: string; role: string; content: string; skill_id?: string; patch_id?: string; created_at: string }> }>(
    `/assistant/threads/${threadId}/messages`,
    { params: { limit } },
  )


export const sendAssistantChat = (data: {
  message: string
  history: any[]
  context?: any
  editor_context?: any
  skill_id?: string
}) => api.post('/assistant/chat', data)

export const sendAssistantChatStream = async (
  data: {
    message: string
    history: any[]
    context?: any
    editor_context?: any
    skill_id?: string
  },
  onChunk: (chunk: string) => void,
  onDone: (result: {
    reply: string
    actions: any[]
    suggestions: string[]
    chips?: any[]
    citations?: any[]
    patch?: any
  }) => void,
  onError: (err: any) => void | Promise<void>,
  onContext?: (contextData: { chips?: any[]; citations?: any[] }) => void,
) => {
  try {
    const baseURL = api.defaults.baseURL || '/api'
    const token = typeof window !== 'undefined' ? window.localStorage.getItem('novel-agent-access-token') : null
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) {
      headers['X-Novel-Agent-Token'] = token
    }

    const res = await fetch(`${baseURL}/assistant/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    })
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    const reader = res.body?.getReader()
    if (!reader) {
      throw new Error('No stream body')
    }
    const decoder = new TextDecoder()
    let buffer = ''
    let receivedDone = false
    let failed = false

    const consumePart = async (part: string) => {
      const trimmed = part.trim()
      if (!trimmed || failed) return
      const eventMatch = trimmed.match(/^event:\s*(\w+)/)
      const dataMatch = trimmed.match(/data:\s*(.+)$/s)
      const eventType = eventMatch ? eventMatch[1] : 'chunk'
      const dataStr = dataMatch ? dataMatch[1] : ''
      let parsed: any
      try {
        parsed = JSON.parse(dataStr)
      } catch {
        failed = true
        await onError(new Error('Malformed assistant stream payload'))
        return
      }
      if (eventType === 'context') {
        if (onContext) {
          onContext(parsed)
        }
      } else if (eventType === 'chunk') {
        onChunk(parsed.chunk || '')
      } else if (eventType === 'done') {
        receivedDone = true
        onDone({
          reply: parsed.reply || '',
          actions: parsed.actions || [],
          suggestions: parsed.suggestions || [],
          chips: parsed.chips || [],
          citations: parsed.citations || [],
          patch: parsed.patch || null,
        })
      } else if (eventType === 'error') {
        failed = true
        await onError(new Error(parsed.error || 'Stream failed'))
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        await consumePart(part)
        if (failed) return
      }
    }
    buffer += decoder.decode()
    if (buffer.trim()) {
      await consumePart(buffer)
    }
    if (!failed && !receivedDone) {
      await onError(new Error('Assistant stream ended without completion'))
    }
  } catch (err) {
    await onError(err)
  }
}

export const getAssistantDiagnose = (ignoredTaskIds?: string[]) =>
  api.get('/assistant/diagnose', { params: { ignored_task_ids: ignoredTaskIds?.join(',') } })

export const fixAssistantIssue = (data: { fix_type: string; payload?: any }) =>
  api.post('/assistant/fix', data)

export const inlineRewrite = (data: { text: string; instruction: string; chapter_id?: string; goal?: string }) =>
  api.post('/assistant/inline-rewrite', data)

export const inlineExpand = (data: { before_text: string; chapter_id?: string; goal?: string }) =>
  api.post('/assistant/inline-expand', data)

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

// ---- Agent bridge (CLI / MCP / external AI) ----

export const getAgentBridgeSettings = () => api.get('/agent/settings')

export const updateAgentBridgeSettings = (data: {
  mcp_mode?: 'auto' | 'offline' | 'http'
  api_url_override?: string
  show_integration_hints?: boolean
}) => api.put('/agent/settings', data)

export const getAgentSnapshot = (params?: { project_id?: string }) =>
  api.get('/agent/snapshot', { params })


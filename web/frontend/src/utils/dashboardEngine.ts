export function inferNextChapterId(existing: { chapter_id: string }[]) {
  if (!existing.length) return '001'
  const maxNum = existing.reduce((max, ch) => {
    const n = parseInt(ch.chapter_id, 10)
    return Number.isNaN(n) ? max : Math.max(max, n)
  }, 0)
  return String(maxNum + 1).padStart(3, '0')
}

export function formatModelLabel(model: { name?: string; id?: string; model?: string }) {
  if (!model) return ''
  return `${model.name || model.id}${model.model ? ` (${model.model})` : ''}`
}

const LOCAL_PROVIDERS = new Set(['ollama', 'vllm', 'lmstudio', 'llama.cpp', 'llamacpp', 'local'])
const MASKED_KEYS = new Set(['', '********', '***', '******'])

function isLocalModel(model: Record<string, any>) {
  const provider = String(model.provider || '').trim().toLowerCase()
  const baseUrl = String(model.base_url || '').trim()
  if (LOCAL_PROVIDERS.has(provider) && !baseUrl) return true
  if (!baseUrl) return false
  try {
    const host = new URL(baseUrl).hostname.toLowerCase()
    return host === 'localhost'
      || host === '::1'
      || host === '127.0.0.1'
      || host.startsWith('127.')
      || host.endsWith('.localhost')
      || host.endsWith('.test')
      || host.endsWith('.invalid')
  } catch {
    return false
  }
}

function hasModelCredentials(model: Record<string, any>) {
  if (isLocalModel(model)) return true
  if (typeof model.has_api_key === 'boolean') return model.has_api_key
  return !MASKED_KEYS.has(String(model.api_key || '').trim())
}

export function resolveEngine(config: Record<string, any>, models: Record<string, any>[]) {
  const llm = config?.llm || {}
  const modelsById = new Map(models.map((model) => [model.id, model]))
  const defaultId = llm.daily_model_id || llm.default_model_id || llm.default?.model_ref
  const defaultModel = defaultId ? modelsById.get(defaultId) : null
  if (defaultModel) {
    if (!hasModelCredentials(defaultModel)) {
      return { ready: false, label: '未配置可用模型', route: 'credentials' }
    }
    return { ready: true, label: formatModelLabel(defaultModel), route: 'daily_model_id' }
  }
  if (llm.default?.provider && llm.default.provider !== 'static') {
    if (!hasModelCredentials(llm.default)) {
      return { ready: false, label: '未配置可用模型', route: 'credentials' }
    }
    return { ready: true, label: llm.default.model || llm.default.provider, route: 'llm.default' }
  }
  if (llm.provider && llm.provider !== 'static') {
    if (!hasModelCredentials(llm)) {
      return { ready: false, label: '未配置可用模型', route: 'credentials' }
    }
    return { ready: true, label: llm.model || llm.provider, route: 'llm' }
  }
  return { ready: false, label: '未配置可用模型', route: 'static' }
}

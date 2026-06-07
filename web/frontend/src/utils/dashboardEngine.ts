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

export function resolveEngine(config: Record<string, any>, models: Record<string, any>[]) {
  const llm = config?.llm || {}
  const modelsById = new Map(models.map((model) => [model.id, model]))
  const defaultId = llm.daily_model_id || llm.default_model_id || llm.default?.model_ref
  const defaultModel = defaultId ? modelsById.get(defaultId) : null
  if (defaultModel) {
    return { ready: true, label: formatModelLabel(defaultModel), route: 'daily_model_id' }
  }
  if (llm.default?.provider && llm.default.provider !== 'static') {
    return { ready: true, label: llm.default.model || llm.default.provider, route: 'llm.default' }
  }
  if (llm.provider && llm.provider !== 'static') {
    return { ready: true, label: llm.model || llm.provider, route: 'llm' }
  }
  return { ready: false, label: '未配置可用模型', route: 'static' }
}
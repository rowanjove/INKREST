export type PetChatAction = {
  type: string
  label: string
  payload?: Record<string, unknown>
}

const ALLOWED_TYPES = new Set([
  'navigate',
  'factory_intent',
  'test_model',
  'retry_task',
  'auto_repair_chapter',
  'rerun_gate',
  'inspect_gate_detail',
])

const GENERATING_TYPES = new Set(['retry_task', 'auto_repair_chapter', 'rerun_gate'])
const FACTORY_INTENTS = new Set(['create', 'plan', 'run', 'monitor', 'repair', 'export'])

function isSafeRoute(route: string): boolean {
  if (!route.startsWith('/') || route.startsWith('//')) return false
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(route)) return false
  return true
}

export function productionConfirmPath(type: string, payload: Record<string, unknown> = {}): string {
  const chapterId = String(payload.chapter_id || '').trim()
  if (type === 'retry_task') return '/production?intent=novel_continue&confirm=1'
  if (type === 'auto_repair_chapter' || type === 'rerun_gate') {
    return chapterId ? `/production?tab=reviews&chapter=${encodeURIComponent(chapterId)}` : '/production?tab=reviews'
  }
  return '/production'
}

export function sanitizePetAction(action: PetChatAction | null | undefined): PetChatAction | null {
  if (!action || !ALLOWED_TYPES.has(action.type)) return null
  const label = String(action.label || action.type)
  const payload = action.payload && typeof action.payload === 'object' ? { ...action.payload } : {}
  if (action.type === 'navigate') {
    const route = String(payload.route || '')
    if (!isSafeRoute(route)) return null
    return { type: 'navigate', label, payload: { route } }
  }
  if (action.type === 'factory_intent') {
    const intent = String(payload.intent || '')
    if (!FACTORY_INTENTS.has(intent)) return null
    return { type: 'factory_intent', label, payload: { intent } }
  }
  if (GENERATING_TYPES.has(action.type)) {
    return { type: 'navigate', label, payload: { route: productionConfirmPath(action.type, payload) } }
  }
  const chapterId = String(payload.chapter_id || '').trim()
  return {
    type: action.type,
    label,
    payload: chapterId ? { chapter_id: chapterId } : {},
  }
}

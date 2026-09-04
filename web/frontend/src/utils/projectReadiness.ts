/** 工作台「开书清单」— 与 openAutoRunDialog 门槛一致 */

export const CORE_WRITING_ASSETS = [
  'world_bible',
  'style_guide',
  'rules',
  'sensitive_words',
] as const

export interface ReadinessItem {
  id: string
  label: string
  ok: boolean
  route: string
  hint?: string
  /** 黄标提示，不阻断自动生成 */
  warn?: boolean
}

export type VectorReadinessContext = {
  semanticSearchEffective: boolean
  vectorEnabled: boolean
  vectorBlocksContinue?: boolean
  embeddingBackend?: string
  chromadbAvailable?: boolean
  embeddingBackendHint?: string
  vectorReadinessLevel?: string
}

export type ServerReadinessSnapshot = {
  ok?: boolean
  pending?: Array<{ id: string; label: string }>
  arc_queue_stale?: { stale?: boolean; message?: string }
  remaining_chapters?: number
  factory_mode?: string
}

const SERVER_PENDING_ROUTES: Record<string, string> = {
  engine: '/config',
  outline: '/outline',
  outline_corrupt: '/outline',
  title: '/outline',
  assets: '/outline',
  quota: '/outline',
  vector: '/config',
  embedding: '/config',
}

/** Merge `/novel/readiness` with embedding status for UI gates and banners. */
export function resolveVectorContextFromApis(
  readyData: Record<string, unknown> | null | undefined,
  embData: Record<string, unknown> | null | undefined,
): VectorReadinessContext {
  const vectorBlocksContinue = Boolean(readyData?.vector_blocks_continue)
  const semanticFromEmb = Boolean(embData?.semantic_search_effective)
  return {
    semanticSearchEffective: vectorBlocksContinue ? false : semanticFromEmb,
    vectorBlocksContinue,
    vectorEnabled: embData?.vector_enabled !== false,
    embeddingBackend: String(readyData?.embedding_backend || ''),
    chromadbAvailable: Boolean(readyData?.chromadb_available),
    embeddingBackendHint: String(readyData?.embedding_backend_hint || ''),
    vectorReadinessLevel: String(readyData?.vector_readiness_level || 'auto'),
  }
}

const LONG_FORM_SCALES = ['long', 'epic', 'infinite'] as const

export function isLongFormScale(workScale: string): boolean {
  return (LONG_FORM_SCALES as readonly string[]).includes(workScale)
}

function chromadbExpectationUnmet(ctx: {
  workScale?: string
  vectorEnabled?: boolean
  embeddingBackend?: string
  chromadbAvailable?: boolean
}): boolean {
  if (ctx.vectorEnabled === false) return false
  if (!isLongFormScale(ctx.workScale || '')) return false
  if (ctx.chromadbAvailable) return false
  const backend = String(ctx.embeddingBackend || '').toLowerCase()
  return backend === 'chromadb' || backend === ''
}

export function coreAssetsReady(
  assets: Array<{ name: string; size?: number }>,
): boolean {
  return CORE_WRITING_ASSETS.every((name) => {
    const asset = assets.find((a) => a.name === name)
    return Boolean(asset && (asset.size ?? 0) > 0)
  })
}

export function outlinePlanningReady(outline: Record<string, unknown> | null): boolean {
  if (!outline) return false
  const macro = Array.isArray(outline.macro_outline) ? outline.macro_outline : []
  if (!macro.length || outline.planning_status === 'draft') return false
  if (macro.length !== 1) return true
  const arc = macro[0] as Record<string, unknown> | undefined
  if (!arc) return false
  const placeholder =
    String(arc.name || '') === '起始卷'
    && String(arc.goal || '') === '确立主线与读者抓手'
    && String(arc.turning_point || '') === '待定'
    && String(arc.payoff || '') === '待定'
  return !placeholder
}

export function buildReadinessItems(opts: {
  engineReady: boolean
  outline: Record<string, unknown> | null
  assets: Array<{ name: string; size?: number }>
  maxAvailableChapters: number
  semanticSearchEffective?: boolean
  vectorEnabled?: boolean
  workScale?: string
  embeddingBackend?: string
  chromadbAvailable?: boolean
  embeddingBackendHint?: string
  vectorReadinessLevel?: string
  vectorBlocksContinue?: boolean
  arcQueueStale?: boolean
}): ReadinessItem[] {
  const outline = opts.outline
  const planningReady = outlinePlanningReady(outline)
  const scale = opts.workScale || String((outline?.scale_profile as { scale?: string })?.scale || '')
  const vectorOn = opts.vectorEnabled !== false
  const semanticOk = opts.semanticSearchEffective !== false
  const longForm = isLongFormScale(scale)
  const chromaMissing = chromadbExpectationUnmet({
    workScale: scale,
    vectorEnabled: opts.vectorEnabled,
    embeddingBackend: opts.embeddingBackend,
    chromadbAvailable: opts.chromadbAvailable,
  })
  const vectorBlocked =
    Boolean(opts.vectorBlocksContinue) ||
    (opts.vectorReadinessLevel === 'block' && vectorOn && !semanticOk)
  const vectorWarn = vectorOn && !vectorBlocked && (!semanticOk || chromaMissing)
  const embeddingHint = (() => {
    if (!vectorOn) return '短篇/微型档默认关闭向量，无需配置'
    if (chromaMissing) {
      return (
        opts.embeddingBackendHint ||
        '长篇默认 ChromaDB 向量；请安装 chromadb 或在设置中配置真实 Embedding'
      )
    }
    if (longForm) {
      return opts.embeddingBackend === 'chromadb'
        ? '长篇连写使用 ChromaDB 召回；stub 时跨章去重与伏笔召回不可用'
        : '长篇连写强烈建议配置 BGE/云端 Embedding；stub 时跨章去重与伏笔召回不可用'
    }
    return '设置 → Embedding：stub 时跨章去重/伏笔召回不可用'
  })()
  const items: ReadinessItem[] = [
    {
      id: 'engine',
      label: '日常模型可用（非 Static 占位）',
      ok: opts.engineReady,
      route: '/config',
      hint: '设置 → 模型路由',
    },
    {
      id: 'outline',
      label: '已生成并保存大纲（含卷纲）',
      ok: planningReady,
      warn: Boolean(opts.arcQueueStale && planningReady),
      route: '/outline',
      hint: !planningReady
        ? '请先生成并保存可执行卷纲；快速建书的占位骨架不能直接生产'
        : opts.arcQueueStale
        ? '卷队列与大纲不一致，确认连写时会自动同步'
        : undefined,
    },
    {
      id: 'title',
      label: '已确定最终书名',
      ok: Boolean(outline?.chosen_title),
      route: '/outline',
      hint: '在大纲页从候选书名中选定',
    },
    {
      id: 'assets',
      label: '核心写作资产齐全',
      ok: coreAssetsReady(opts.assets),
      route: '/outline',
      hint: '保存大纲可联动初始化四类资产',
    },
    {
      id: 'quota',
      label: '未达大纲章节上限',
      ok: opts.maxAvailableChapters > 0,
      route: '/outline',
      hint: '可在体量架构中提高目标章数',
    },
    {
      id: 'embedding',
      label: vectorOn
        ? longForm && opts.embeddingBackend === 'chromadb'
          ? '语义向量（ChromaDB）'
          : '语义向量可用（非 stub）'
        : '语义向量（当前体量已关闭）',
      ok: !vectorBlocked,
      warn: vectorWarn,
      route: '/config',
      hint: embeddingHint,
    },
  ]
  return items
}

/** Map backend pending ids (e.g. vector) onto local checklist rows. */
export function mergeServerReadinessPending(
  items: ReadinessItem[],
  pending: Array<{ id: string; label: string }> | undefined,
): ReadinessItem[] {
  if (!pending?.length) return items
  const pendingByLocalId = new Map<string, { id: string; label: string }>()
  for (const row of pending) {
    const localId = row.id === 'vector' ? 'embedding' : row.id
    pendingByLocalId.set(localId, row)
  }
  const merged = items.map((item) => {
    const serverRow = pendingByLocalId.get(item.id)
    if (!serverRow) return item
    pendingByLocalId.delete(item.id)
    return { ...item, ok: false, hint: serverRow.label }
  })
  for (const [localId, row] of pendingByLocalId) {
    merged.push({
      id: localId,
      label: row.label,
      ok: false,
      route: SERVER_PENDING_ROUTES[localId] || '/workspace',
      hint: row.label,
    })
  }
  return merged
}

export function readinessAllOk(items: ReadinessItem[]): boolean {
  return items.length > 0 && items.every((i) => i.ok)
}

/** Gate连写：清单红灯才阻断。缺卷队列由确认连写时自动同步，不挡在全绿之后。 */
export function readinessCanContinue(opts: {
  items: ReadinessItem[]
  serverOk?: boolean
}): boolean {
  return opts.serverOk !== false && readinessAllOk(opts.items)
}

/** 存在未通过项（红灯），warn 黄标不阻断连写 */
export function readinessHasRed(items: ReadinessItem[]): boolean {
  return items.some((i) => !i.ok)
}

export type ReadinessTrafficLight = 'green' | 'red'

export function readinessTrafficLight(items: ReadinessItem[]): ReadinessTrafficLight {
  return readinessHasRed(items) ? 'red' : 'green'
}

/** 长篇且向量未就绪：黄标建议，不阻断连写 */
export function longFormVectorWarn(opts: {
  workScale: string
  vectorEnabled?: boolean
  semanticSearchEffective?: boolean
  embeddingBackend?: string
  chromadbAvailable?: boolean
  vectorReadinessLevel?: string
}): boolean {
  if (!isLongFormScale(opts.workScale)) return false
  if (opts.vectorEnabled === false) return false
  if (opts.vectorReadinessLevel === 'ignore') return false
  if (opts.semanticSearchEffective === false) return true
  return chromadbExpectationUnmet(opts)
}

export const LONG_FORM_VECTOR_WARN_TEXT =
  '长篇连写强烈建议配置 BGE 或云端 Embedding；stub 时跨章去重与伏笔召回不可用。'

/** 创建成功弹窗文案（与清单一致） */
export function postCreateChecklistLines(preferOutline: boolean): string[] {
  return [
    '1. 设置：确认日常模型可用',
    preferOutline
      ? '2. 大纲：生成卷纲并确定最终书名（快速创建已用书名预填，请保存大纲）'
      : '2. 大纲：确认最终书名与卷纲',
    '3. 大纲：保存后检查核心写作资产（世界观/风格/规则/敏感词）',
    '4. 生产中心：准备状态满足后确认「继续生产」；暂停后先处理审校队列',
  ]
}

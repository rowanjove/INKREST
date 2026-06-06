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

export function coreAssetsReady(
  assets: Array<{ name: string; size?: number }>,
): boolean {
  return CORE_WRITING_ASSETS.every((name) => {
    const asset = assets.find((a) => a.name === name)
    return Boolean(asset && (asset.size ?? 0) > 0)
  })
}

export function buildReadinessItems(opts: {
  engineReady: boolean
  outline: Record<string, unknown> | null
  assets: Array<{ name: string; size?: number }>
  maxAvailableChapters: number
  /** false when embedding is stub but project expects vectors */
  semanticSearchEffective?: boolean
  vectorEnabled?: boolean
  workScale?: string
}): ReadinessItem[] {
  const outline = opts.outline
  const macro = (outline?.macro_outline as unknown[]) || []
  const scale = opts.workScale || String((outline?.scale_profile as { scale?: string })?.scale || '')
  const vectorOn = opts.vectorEnabled !== false
  const semanticOk = opts.semanticSearchEffective !== false
  const longForm = ['long', 'epic', 'infinite'].includes(scale)
  return [
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
      ok: macro.length > 0,
      route: '/outline',
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
      label: vectorOn ? '语义向量可用（非 stub）' : '语义向量（当前体量已关闭）',
      ok: true,
      warn: vectorOn && !semanticOk,
      route: '/config',
      hint: vectorOn
        ? longForm
          ? '长篇连写强烈建议配置 BGE/云端 Embedding；stub 时跨章去重与伏笔召回不可用'
          : '设置 → Embedding：stub 时跨章去重/伏笔召回不可用'
        : '短篇/微型档默认关闭向量，无需配置',
    },
  ]
}

export function readinessAllOk(items: ReadinessItem[]): boolean {
  return items.length > 0 && items.every((i) => i.ok)
}

/** 存在未通过项（红灯），warn 黄标不阻断连写 */
export function readinessHasRed(items: ReadinessItem[]): boolean {
  return items.some((i) => !i.ok)
}

export type ReadinessTrafficLight = 'green' | 'red'

export function readinessTrafficLight(items: ReadinessItem[]): ReadinessTrafficLight {
  return readinessHasRed(items) ? 'red' : 'green'
}

const LONG_FORM_SCALES = ['long', 'epic', 'infinite'] as const

export function isLongFormScale(workScale: string): boolean {
  return (LONG_FORM_SCALES as readonly string[]).includes(workScale)
}

/** 长篇且向量未就绪：黄标建议，不阻断连写 */
export function longFormVectorWarn(opts: {
  workScale: string
  vectorEnabled?: boolean
  semanticSearchEffective?: boolean
}): boolean {
  if (!isLongFormScale(opts.workScale)) return false
  if (opts.vectorEnabled === false) return false
  return opts.semanticSearchEffective === false
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
    '4. 工作台：开书清单全绿后点「连写启动」；暂停后到章节维护点「继续写书」',
  ]
}
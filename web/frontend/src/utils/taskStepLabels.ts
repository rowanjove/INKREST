/** 流水线步骤中文名 — 任务流水、山山状态等共用 */
export const TASK_STEP_LABELS: Record<string, string> = {
  init: '初始化',
  planner: '规划章节剧情',
  writer: 'AI 写作正文初稿',
  merge: '合并场景段落',
  stitch_editor: '拼接润色与消除接缝',
  style_editor: '文风优化与润色',
  continuity_checker: '连续性冲突检查',
  chapter_summary: '生成本章内容摘要',
  auditor: '正文安全与合规审校',
  sensitive_scan: '敏感词安全扫描',
  state_update: '同步最新人物与大纲状态',
  vector_index: '更新向量检索索引',
  quality_guard: '质量门禁检查',
  plugin_hook: '插件钩子',
  chief_editor: '总编大纲规划',
  managing_editor: '主编章节拆分',
  chapter_planner: '大纲编剧扩写',
  rewriter: '自动重写修正',
}

export function formatTaskStep(step?: string | null): string {
  const key = String(step || '').trim()
  if (!key) return '运行中'
  return TASK_STEP_LABELS[key] || key
}
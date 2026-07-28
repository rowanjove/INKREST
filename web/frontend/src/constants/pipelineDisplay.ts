/** 生产线展示块：与侧栏运行状态、tasks store 的 step 对齐 */

export type ProductionBlock = {
  id: string
  label: string
  desc: string
  steps: string[]
}

export const PRODUCTION_BLOCKS: ProductionBlock[] = [
  {
    id: 'queue',
    label: '卷队列',
    desc: '同步卷纲与批量调度',
    steps: ['ensure_queue', 'managing_editor', 'novel_batch', 'novel_autopilot'],
  },
  {
    id: 'plan',
    label: '大纲编剧',
    desc: '章节扩写与场景规划',
    steps: ['init', 'chapter_planner', 'planner'],
  },
  {
    id: 'write',
    label: '写手 Agent',
    desc: '按场景写出正文初稿',
    steps: ['writer', 'merge'],
  },
  {
    id: 'polish',
    label: '拼接润色',
    desc: '接缝修复与文风统一',
    steps: ['stitch_editor', 'style_editor', 'continuity_checker', 'chapter_summary'],
  },
  {
    id: 'audit',
    label: '审校',
    desc: '安全审校与字数修正',
    steps: ['auditor', 'sensitive_scan', 'rewriter', 'length_fix'],
  },
  {
    id: 'gate',
    label: '审核 QA',
    desc: '门禁、状态同步与索引',
    steps: ['unified_gate', 'quality_guard', 'approval', 'state_update', 'vector_index', 'plugin_hook'],
  },
]

export const PIPELINE_STEP_LABELS: Record<string, string> = {
  init: '初始化',
  ensure_queue: '同步卷队列',
  managing_editor: '主编拆卷',
  chapter_planner: '章节扩写',
  planner: '场景规划',
  writer: '写作引擎',
  merge: '场景合并',
  stitch_editor: '接缝修复',
  style_editor: '文风优化',
  continuity_checker: '连续性检查',
  chapter_summary: '章节总结',
  auditor: '安全审校',
  state_extractor: '状态提取',
  rewriter: '定向重写',
  length_fix: '字数修正',
  unified_gate: '统一门禁',
  quality_guard: '质量门禁',
  approval: '审批闸',
  sensitive_scan: '敏感词扫描',
  state_update: '状态同步',
  vector_index: '向量索引',
  plugin_hook: '插件钩子',
  novel_batch: '批量续跑',
  novel_autopilot: '全书自动续轮',
}
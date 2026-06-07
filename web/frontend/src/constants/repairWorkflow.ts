/** 半自动修章 / 外站审核 — 全站一致文案 */

export const INTERNAL_GATE_HINT =
  '内部门禁（栖墨统一门禁）：检查正文质量、敏感词与连续性；未通过会阻断落库并暂停全书批量。'

export const EXTERNAL_AUDIT_HINT =
  '外站审核（平台试发）：网文平台 AI 审核与栖墨门禁独立；需复制正文试发，不过则改稿后再续跑。'

export const DUAL_AUDIT_HINT = `${INTERNAL_GATE_HINT} ${EXTERNAL_AUDIT_HINT} 修章顺序：写作页改正文 → 复制试发 → 重跑审校或查统一门禁 → 通过后再「继续写书」。`

export const SEMI_AUTO_STEPS = [
  '章节维护看待处理章节',
  '写作页或章节详情改正文',
  '复制全文到平台试审',
  '重试审校 / 查统一门禁',
  '工作台继续写书',
] as const

export type SemiAutoRepairAction =
  | 'scroll-alerts'
  | 'open-writer'
  | 'copy-trial'
  | 'open-gate'
  | 'continue-batch'

export interface SemiAutoRepairStep {
  id: string
  label: string
  desc: string
  action: SemiAutoRepairAction
}

export const SEMI_AUTO_REPAIR_STEPS: SemiAutoRepairStep[] = [
  {
    id: 'monitor',
    label: '展开待处理',
    desc: '展开下方待处理章节列表',
    action: 'scroll-alerts',
  },
  {
    id: 'edit',
    label: '改正文',
    desc: '写作页或章节详情修改正文',
    action: 'open-writer',
  },
  {
    id: 'copy',
    label: '复制试审',
    desc: '复制全文到网文平台试审',
    action: 'copy-trial',
  },
  {
    id: 'gate',
    label: '重试审校',
    desc: '重跑审校或查看统一门禁报告',
    action: 'open-gate',
  },
  {
    id: 'resume',
    label: '继续写书',
    desc: '修完后在工作台一键续跑批量',
    action: 'continue-batch',
  },
]

export const LANE_A_HINT = '全书连写：工作台开书清单 → 连写启动；暂停后章节维护 → 继续写书。'

export const LANE_B_HINT =
  '半自动修章：门禁或外站不过时，先改稿再续批量，不要直接无上限续跑。'
import type { PipelineAlert } from '../stores/pipelineAlerts'

export function isQualityBlocked(item: {
  last_stage?: string
  quality?: { blocked_by?: string[] }
}) {
  return (
    item.last_stage === 'quality_blocked' || Boolean(item.quality?.blocked_by?.length)
  )
}

export function isBatchRetry(item: { last_stage?: string }) {
  return item.last_stage === 'batch_retry'
}

export function isExternalPending(item: { last_stage?: string }) {
  return item.last_stage === 'external_review_pending'
}

export function needsRepairActions(item: {
  last_stage?: string
  quality?: { blocked_by?: string[] }
}) {
  return isQualityBlocked(item) || isBatchRetry(item) || isExternalPending(item)
}

export function canRerunAudit(item: PipelineAlert) {
  return !isExternalPending(item)
}

export interface PendingStepCardDef {
  id: string
  index: number
  label: string
  desc: string
  bulkAction?: 'resume-audit' | 'rerun-gate' | 'external-passed' | 'rewrite-batch'
  filter: (item: PipelineAlert) => boolean
}

export const PENDING_STEP_CARDS: PendingStepCardDef[] = [
  {
    id: 'gate',
    index: 1,
    label: '门禁阻断',
    desc: '统一门禁未通过，改稿后重跑门禁',
    bulkAction: 'rerun-gate',
    filter: isQualityBlocked,
  },
  {
    id: 'retry',
    index: 2,
    label: '批量跳过',
    desc: '连写熔断跳过，待重试审校',
    bulkAction: 'resume-audit',
    filter: isBatchRetry,
  },
  {
    id: 'external',
    index: 3,
    label: '待外审',
    desc: '内部门禁已过，等平台试审结果',
    bulkAction: 'external-passed',
    filter: isExternalPending,
  },
  {
    id: 'all',
    index: 4,
    label: '全文重跑',
    desc: '按最新方案从头重写选中章',
    bulkAction: 'rewrite-batch',
    filter: () => true,
  },
]
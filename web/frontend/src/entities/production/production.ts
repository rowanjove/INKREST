import type { ProjectSnapshot, TaskStatus, TaskType } from '../project/projectSnapshot'

export type ProductionTab = 'runs' | 'reviews' | 'costs' | 'logs'
export type ProductionTaskFilter = 'all' | 'active' | 'failed' | 'finished'
export type ProductionReviewFilter = 'all' | 'error' | 'warning' | 'external'
export type ProductionActionKind =
  | 'cancel_task'
  | 'resume_audit'
  | 'rerun_gate'
  | 'rewrite'
  | 'external_passed'
  | 'dismiss'

export interface ProductionTask {
  id: string
  project_id: string
  task_type: TaskType
  task_type_label: string
  status: TaskStatus
  status_label: string
  chapter_id: string | null
  goal: string
  attempt: number
  max_attempts: number
  step: string | null
  step_label: string | null
  checkpoint: {
    resumable_from: string | null
    progress: Record<string, unknown> | null
  }
  status_reason: string | null
  failure_code: string | null
  failure_message: string | null
  recovery_action: 'cancel' | 'resume_audit' | 'open_writer' | 'none'
  heartbeat_at: string | null
  lease_expires_at: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface ProductionTaskEvent {
  id: number
  task_id: string
  from_status: TaskStatus | null
  to_status: TaskStatus
  from_status_label: string | null
  to_status_label: string
  reason: string | null
  resumable_from: string | null
  created_at: string
}

export interface ProductionTaskLog {
  id: number
  task_id: string
  level: 'debug' | 'info' | 'warning' | 'error'
  message: string
  step: string
  timestamp: number
  created_at: string
}

export interface ProductionRuntimeLog {
  id: number
  project_id: string
  task_id: string
  timestamp: number
  level: 'debug' | 'info' | 'warn' | 'warning' | 'error'
  step: string
  message: string
  chapter_id: string
  source: string
  type: string
  status?: string
}

export interface ProductionReviewIssue {
  code: string
  label: string
  severity: 'error' | 'warning'
  score: number | null
  details: string[]
}

export interface ProductionReviewItem {
  chapter_id: string
  chapter_title: string
  stage: string
  stage_label: string
  severity: 'error' | 'warning'
  message: string
  overall_score: number | null
  issues: ProductionReviewIssue[]
  completed_stages: string[]
  updated_at: string | number | null
  recommended_action:
    | 'edit_then_gate'
    | 'resume_audit'
    | 'rewrite'
    | 'external_review'
    | 'inspect_report'
    | 'open_writer'
}

export interface ProductionReviewQueue {
  summary: {
    status: string
    total_reports: number
    passed: number
    failed: number
    unreadable: number
    ai_flavor_risks?: number
    open_items: number
    stage_counts: Record<string, number>
  }
  items: ProductionReviewItem[]
}

export interface ProductionWorkspace {
  schema_version: 1
  snapshot: ProjectSnapshot
  tasks: ProductionTask[]
  events: ProductionTaskEvent[]
  task_logs: ProductionTaskLog[]
  runtime_logs: ProductionRuntimeLog[]
  reviews: ProductionReviewQueue
  section_errors: Record<string, string>
  updated_at: string
}

export interface ProductionActionIntent {
  kind: ProductionActionKind
  label: string
  description: string
  confirmLabel: string
  chapterIds: string[]
  taskId?: string
  tone: 'warning' | 'danger' | 'primary'
}

const ACTIVE_STATUSES = new Set<TaskStatus>(['pending', 'claimed', 'running', 'paused'])
const FINISHED_STATUSES = new Set<TaskStatus>(['succeeded', 'cancelled'])
const STEP_LABELS: Record<string, string> = {
  init: '初始化',
  planner: '规划章节剧情',
  writer: '正文写作',
  merge: '合并场景',
  stitch_editor: '消除段落接缝',
  style_editor: '文风润色',
  continuity_checker: '连续性检查',
  chapter_summary: '生成章节摘要',
  auditor: '内容审校',
  sensitive_scan: '敏感内容检查',
  state_update: '同步剧情状态',
  vector_index: '更新检索索引',
  quality_guard: '质量门禁',
  plugin_hook: '扩展处理',
  chief_editor: '总编规划',
  managing_editor: '章节拆分',
  chapter_planner: '章节扩写',
  rewriter: '自动修订',
  audit: '审校检查点',
  export: '导出预览',
}
const REASON_LABELS: Record<string, string> = {
  created: '任务已创建',
  claimed: '执行器已领取任务',
  worker_claimed: '执行器已领取任务',
  started: '任务开始运行',
  worker_started: '任务开始运行',
  completed: '任务已完成',
  failed: '任务执行失败',
  cancelled: '任务已取消',
  user_cancelled: '用户请求中止',
  lease_expired: '执行租约已过期',
  quality_blocked: '质量门禁阻断',
  external_review_pending: '等待外部审校',
  consecutive_failures: '连续失败后暂停',
  retry_scheduled: '已安排重试',
  resumed: '已从检查点恢复',
}

export function productionStepLabel(step?: string | null): string {
  const key = String(step || '').trim()
  if (!key) return '未记录'
  return STEP_LABELS[key] || key.replaceAll('_', ' ')
}

export function productionReasonLabel(reason?: string | null): string {
  const key = String(reason || '').trim()
  if (!key) return ''
  return REASON_LABELS[key] || key.replaceAll('_', ' ')
}

export function taskTone(status: TaskStatus): 'info' | 'warning' | 'success' | 'danger' {
  if (status === 'failed') return 'danger'
  if (status === 'paused' || status === 'pending') return 'warning'
  if (status === 'succeeded') return 'success'
  return 'info'
}

export function filterProductionTasks(
  tasks: readonly ProductionTask[],
  filter: ProductionTaskFilter,
  query: string,
): ProductionTask[] {
  const needle = query.trim().toLocaleLowerCase()
  return tasks.filter((task) => {
    if (filter === 'active' && !ACTIVE_STATUSES.has(task.status)) return false
    if (filter === 'failed' && task.status !== 'failed') return false
    if (filter === 'finished' && !FINISHED_STATUSES.has(task.status)) return false
    if (!needle) return true
    return [
      task.id,
      task.task_type_label,
      task.chapter_id || '',
      task.goal,
      task.step_label || '',
      task.failure_message || '',
    ].some((value) => value.toLocaleLowerCase().includes(needle))
  })
}

export function filterProductionReviews(
  items: readonly ProductionReviewItem[],
  filter: ProductionReviewFilter,
  query: string,
): ProductionReviewItem[] {
  const needle = query.trim().toLocaleLowerCase()
  return items.filter((item) => {
    if (filter === 'error' && item.severity !== 'error') return false
    if (filter === 'warning' && item.severity !== 'warning') return false
    if (filter === 'external' && item.stage !== 'external_review_pending') return false
    if (!needle) return true
    return [
      item.chapter_id,
      item.chapter_title,
      item.stage_label,
      item.message,
      ...item.issues.flatMap((issue) => [issue.label, ...issue.details]),
    ].some((value) => value.toLocaleLowerCase().includes(needle))
  })
}

export function resolveReviewActionTargets(
  kind: Exclude<ProductionActionKind, 'cancel_task'>,
  items: readonly ProductionReviewItem[],
): string[] {
  return items
    .filter((item) => {
      if (kind === 'external_passed') return item.stage === 'external_review_pending'
      if (kind === 'rerun_gate') {
        return ['quality_blocked', 'report_failed'].includes(item.stage)
      }
      if (kind === 'rewrite') {
        return ['quality_blocked', 'report_failed', 'batch_retry'].includes(item.stage)
      }
      if (kind === 'resume_audit') {
        return [
          'quality_blocked',
          'approval_rejected',
          'report_failed',
          'report_invalid',
        ].includes(item.stage)
      }
      return true
    })
    .map((item) => item.chapter_id)
}

export function createProductionActionIntent(
  kind: ProductionActionKind,
  options: { chapterIds?: string[]; taskId?: string } = {},
): ProductionActionIntent {
  const chapterIds = [...new Set(options.chapterIds || [])]
  const scope = chapterIds.length
    ? `${chapterIds.length} 章（${chapterIds.map((id) => `第 ${id} 章`).join('、')}）`
    : '当前任务'
  const copy: Record<
    ProductionActionKind,
    Pick<ProductionActionIntent, 'label' | 'description' | 'confirmLabel' | 'tone'>
  > = {
    cancel_task: {
      label: '中止运行任务',
      description: '将发送中止信号。已完成的步骤不会回滚，当前步骤可能需要等待安全检查点。',
      confirmLabel: '确认中止',
      tone: 'danger',
    },
    resume_audit: {
      label: '重试审校',
      description: `将对${scope}从可恢复检查点继续审校，不会自动改写未确认的正文。`,
      confirmLabel: '确认重试',
      tone: 'warning',
    },
    rerun_gate: {
      label: '重跑质量门禁',
      description: `将用现有正文重新检查${scope}，不会生成新的正文内容。`,
      confirmLabel: '确认重跑',
      tone: 'warning',
    },
    rewrite: {
      label: '重新生产章节',
      description: `将清空${scope}的流水线断点并重新生成，现有正文仍可从修订历史恢复。`,
      confirmLabel: '确认重新生产',
      tone: 'danger',
    },
    external_passed: {
      label: '标记外审通过',
      description: `将把${scope}标记为外部试审已通过，使后续生产可以继续。`,
      confirmLabel: '确认通过',
      tone: 'primary',
    },
    dismiss: {
      label: '标记问题已处理',
      description: `将从待处理队列移除${scope}；正文和质量报告不会被删除。`,
      confirmLabel: '确认已处理',
      tone: 'primary',
    },
  }
  return {
    kind,
    ...copy[kind],
    chapterIds,
    taskId: options.taskId,
  }
}

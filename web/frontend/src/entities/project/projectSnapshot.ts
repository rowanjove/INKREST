export type TaskStatus =
  | 'pending'
  | 'claimed'
  | 'running'
  | 'paused'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export type TaskType =
  | 'chapter'
  | 'chapter_batch'
  | 'novel_plan'
  | 'chapter_plan'
  | 'novel_run'
  | 'arc_run'
  | 'novel_continue'
  | 'novel_autopilot'
  | 'embedding_setup'
  | 'export'

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  pending: '等待中',
  claimed: '已领取',
  running: '运行中',
  paused: '已暂停',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

export const ACTIVE_TASK_STATUSES = new Set<TaskStatus>([
  'pending',
  'claimed',
  'running',
  'paused',
])

export function isActiveTaskStatus(status: TaskStatus): boolean {
  return ACTIVE_TASK_STATUSES.has(status)
}

export interface SnapshotTask {
  id: string
  project_id: string
  task_type: TaskType
  status: TaskStatus
  payload_json: Record<string, unknown>
  result_json: Record<string, unknown> | null
  attempt: number
  max_attempts: number
  claim_token: null
  lease_expires_at: string | null
  heartbeat_at: string | null
  checkpoint: Record<string, unknown> | null
  status_reason: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface SnapshotProject {
  id: string
  name: string
  description?: string
  genre?: string
  platform?: string
  scale?: string
  created_at?: string | null
  updated_at?: string | null
}

export interface ReadinessSnapshot {
  ok: boolean
  pending: Array<Record<string, unknown>>
  warnings: string[]
  [key: string]: unknown
}

export interface OutlineProgress {
  exists: boolean
  valid: boolean
  title: string
  arc_count: number
  planned_chapters: number
  target_chapters: number
  error: string | null
}

export interface ChapterProgress {
  authoritative_completed: number
  completed_chapter_ids?: string[]
  total_words?: number
  pending_total?: number
  batch_status?: string
  batch_paused?: boolean
  pause_reason?: string
  remaining_chapters?: number
  [key: string]: unknown
}

export interface BlockingIssue {
  code: string
  label: string
  severity: 'error' | 'warning' | 'info' | string
  source: string
  detail?: string
  chapter_id?: string | null
  errors?: Array<Record<string, unknown>>
}

export interface QualitySummary {
  status: string
  total_reports: number
  passed: number
  failed: number
  unreadable?: number
  ai_flavor_risks?: number
  latest_issue?: Record<string, unknown> | null
}

export interface CostSummary {
  project_id?: string
  persisted: {
    call_count?: number
    input_tokens?: number
    output_tokens?: number
    total_tokens: number
    total_cost_cny: number
    today_tokens?: number
    today_cost_cny?: number
  }
  persisted_error?: string | null
  recent_rounds?: Array<Record<string, unknown>>
  disclaimer?: string
}

export interface SnapshotAction {
  id: string
  label: string
  kind: 'navigate' | 'intent' | string
  target: string
  enabled: boolean
  reason?: string
}

export interface ProjectSnapshot {
  project: SnapshotProject
  workflow_mode: 'assisted' | 'factory'
  readiness: ReadinessSnapshot
  outline_progress: OutlineProgress
  chapter_progress: ChapterProgress
  active_tasks: SnapshotTask[]
  blocking_issues: BlockingIssue[]
  quality_summary: QualitySummary
  cost_summary: CostSummary
  next_actions: SnapshotAction[]
  updated_at: string
}

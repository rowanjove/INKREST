import type {
  ProjectSnapshot,
  SnapshotAction,
  TaskType,
} from '../../entities/project/projectSnapshot'
import type { BackendStatus } from '../bootstrap/useDesktopLifecycle'

export type DiagnosticTone = 'ready' | 'active' | 'warning' | 'danger' | 'checking'

export interface DiagnosticsSummary {
  tone: DiagnosticTone
  label: string
  blockerCount: number
  warningCount: number
  activeTaskCount: number
}

const QUALITY_STATUS_LABELS: Record<string, string> = {
  missing: '暂无报告',
  low: '质量偏低',
  stable: '质量稳定',
  passed: '质量通过',
  failing: '质量未通过',
  failed: '质量未通过',
  unknown: '状态未知',
}

const TASK_TYPE_LABELS: Record<TaskType, string> = {
  chapter: '单章生成',
  chapter_batch: '批量章节',
  novel_plan: '小说策划',
  chapter_plan: '章节策划',
  novel_run: '全书生产',
  arc_run: '分卷生产',
  novel_continue: '续写小说',
  novel_autopilot: '自动生产',
  embedding_setup: '记忆索引',
  export: '作品导出',
}

export function qualityStatusLabel(status: string): string {
  return QUALITY_STATUS_LABELS[status] || '状态未知'
}

export function taskTypeLabel(type: TaskType): string {
  return TASK_TYPE_LABELS[type]
}

export function destinationForAction(action: SnapshotAction): string {
  return action.kind === 'navigate'
    ? action.target
    : `/workspace?intent=${encodeURIComponent(action.target)}`
}

export function buildDiagnosticsSummary(
  snapshot: ProjectSnapshot | null,
  backendStatus: BackendStatus,
  backendUnreachable: boolean,
): DiagnosticsSummary {
  const blockerCount = snapshot?.blocking_issues
    .filter((issue) => issue.severity === 'error').length || 0
  const issueWarningCount = snapshot?.blocking_issues
    .filter((issue) => issue.severity !== 'error').length || 0
  const readinessWarningCount = snapshot?.readiness.warnings.length || 0
  const warningCount = issueWarningCount + readinessWarningCount
  const activeTaskCount = snapshot?.active_tasks.length || 0

  if (backendStatus === 'restarting') {
    return { tone: 'checking', label: '服务重启中', blockerCount, warningCount, activeTaskCount }
  }
  if (backendStatus !== 'online' || backendUnreachable) {
    return { tone: 'danger', label: '服务离线', blockerCount, warningCount, activeTaskCount }
  }
  if (!snapshot) {
    return { tone: 'checking', label: '正在读取状态', blockerCount, warningCount, activeTaskCount }
  }
  if (blockerCount) {
    return { tone: 'danger', label: `${blockerCount} 项阻断`, blockerCount, warningCount, activeTaskCount }
  }
  if (warningCount) {
    return { tone: 'warning', label: `${warningCount} 项提醒`, blockerCount, warningCount, activeTaskCount }
  }
  if (activeTaskCount) {
    return { tone: 'active', label: `${activeTaskCount} 个任务进行中`, blockerCount, warningCount, activeTaskCount }
  }
  return { tone: 'ready', label: '运行正常', blockerCount, warningCount, activeTaskCount }
}

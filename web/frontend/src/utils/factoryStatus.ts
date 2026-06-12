import type {
  FactoryDashboard,
  FactoryMode,
  FactoryRiskLevel,
  FactoryState,
} from '../types/factory'

export type FactoryActionIntent =
  | 'create'
  | 'plan'
  | 'run'
  | 'monitor'
  | 'repair'
  | 'export'

export interface FactoryPrimaryAction {
  label: string
  intent: FactoryActionIntent
}

const MODE_LABELS: Record<FactoryMode, string> = {
  newbie_auto: '新手全自动',
  author_copilot: '作者协作',
  platform_review: '平台过审',
  longform_stable: '长篇稳定',
  studio: '工作室生产',
}

const STATE_LABELS: Record<FactoryState, string> = {
  empty: '等待开书',
  planning: '计划待完善',
  ready: '可以生产',
  running: '生产中',
  blocked: '等待修复',
  complete: '生产完成',
}

export function formatFactoryMode(mode: FactoryMode): string {
  return MODE_LABELS[mode] ?? mode
}

export function formatFactoryState(state: FactoryState): string {
  return STATE_LABELS[state] ?? state
}

export function getFactoryTone(riskLevel: FactoryRiskLevel): 'success' | 'warning' | 'danger' {
  if (riskLevel === 'high') return 'danger'
  if (riskLevel === 'medium') return 'warning'
  return 'success'
}

export function getFactoryPrimaryAction(dashboard: FactoryDashboard): FactoryPrimaryAction {
  switch (dashboard.factory_status.state) {
    case 'empty':
      return { label: '新建作品', intent: 'create' }
    case 'planning':
      return { label: '生成生产计划', intent: 'plan' }
    case 'running':
      return { label: '查看生产进度', intent: 'monitor' }
    case 'blocked':
      return { label: '自动修复', intent: 'repair' }
    case 'complete':
      return { label: '导出作品', intent: 'export' }
    case 'ready':
    default:
      return { label: '开始生产', intent: 'run' }
  }
}

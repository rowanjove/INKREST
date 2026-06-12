export type FactoryMode =
  | 'newbie_auto'
  | 'author_copilot'
  | 'platform_review'
  | 'longform_stable'
  | 'studio'

export type FactoryState =
  | 'empty'
  | 'planning'
  | 'ready'
  | 'running'
  | 'blocked'
  | 'complete'

export type ProductionPlanStatus = 'missing' | 'planning' | 'ready'
export type FactoryRiskLevel = 'low' | 'medium' | 'high'
export type FactoryStepState = 'done' | 'active' | 'warning' | 'blocked' | 'idle'
export type FactoryRepairAction = 'auto_repair' | 'rerun_gate' | 'manual_edit'

export interface FactoryProject {
  id: string | null
  name: string
  scale: string
  mode: FactoryMode
}

export type FactoryAutomationLevel = 'high' | 'balanced' | 'managed'

export interface FactoryModeProfile {
  mode: FactoryMode
  label: string
  automation_level: FactoryAutomationLevel
  priorities: string[]
  operator_hint: string
}

export interface ProductionPlanReadiness {
  ok: number
  total: number
  missing: string[]
}

export interface ProductionPlanSummary {
  status: ProductionPlanStatus
  title: string
  selling_points: string[]
  target_chapters: number
  planned_chapters: number
  readiness: ProductionPlanReadiness
}

export interface FactoryStatusSummary {
  state: FactoryState
  current_stage: string
  completed_chapters: number
  target_chapters: number
  running_tasks: number
  risk_level: FactoryRiskLevel
}

export interface FactoryPipelineStep {
  id: string
  label: string
  state: FactoryStepState
}

export interface FactoryRepairItem {
  chapter_id: string
  title: string
  reason: string
  recommended_action: FactoryRepairAction
  manual_hint: string
  last_stage?: string
  source?: string
}

export interface FactoryRepairSummary {
  blocked_count: number
  items: FactoryRepairItem[]
}

export interface FactoryExportSummary {
  txt_available: boolean
  epub_available: boolean
  pdf_available: boolean
}

export interface FactoryDashboard {
  project: FactoryProject
  production_plan: ProductionPlanSummary
  factory_status: FactoryStatusSummary
  mode_profile: FactoryModeProfile
  pipeline: FactoryPipelineStep[]
  repair: FactoryRepairSummary
  exports: FactoryExportSummary
}

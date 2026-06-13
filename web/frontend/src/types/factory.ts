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

export type FactoryCommandIntent = 'create' | 'plan' | 'run' | 'monitor' | 'repair' | 'export'
export type FactoryCommandTone = 'primary' | 'success' | 'warning' | 'danger' | 'info'

export interface FactoryCommand {
  id: string
  label: string
  intent: FactoryCommandIntent
  tone: FactoryCommandTone
  reason: string
}

export type FactoryBriefSeverity = 'success' | 'warning' | 'danger' | 'info'

export interface FactoryOperatorBrief {
  severity: FactoryBriefSeverity
  next_intent: FactoryCommandIntent
  summary: string
  details: string
}

export interface ProductionPlanReadiness {
  ok: number
  total: number
  missing: string[]
}

export type ProductionPlanNextStepIntent = 'plan' | 'asset'

export interface ProductionPlanNextStep {
  id: string
  label: string
  description: string
  intent: ProductionPlanNextStepIntent
  route: string
}

export interface ProductionPlanSummary {
  status: ProductionPlanStatus
  title: string
  selling_points: string[]
  target_chapters: number
  planned_chapters: number
  readiness: ProductionPlanReadiness
  next_steps: ProductionPlanNextStep[]
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

export type FactoryQualityStatus = 'missing' | 'passed' | 'blocked'

export interface FactoryQualityIssue {
  chapter_id: string
  blocked_by: string[]
  ai_flavor_risk: string
}

export interface FactoryQualitySummary {
  status: FactoryQualityStatus
  total_reports: number
  passed: number
  failed: number
  ai_flavor_risks: number
  latest_issue: FactoryQualityIssue | null
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
  operator_brief: FactoryOperatorBrief
  commands: FactoryCommand[]
  pipeline: FactoryPipelineStep[]
  quality_summary: FactoryQualitySummary
  repair: FactoryRepairSummary
  exports: FactoryExportSummary
}

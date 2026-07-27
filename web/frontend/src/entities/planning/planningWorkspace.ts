export type PlanningEntityKind =
  | 'outline'
  | 'character'
  | 'location'
  | 'organization'
  | 'object'
  | 'foreshadow'
  | 'rule'

export interface PlanningEntity {
  id: string
  kind: PlanningEntityKind | string
  name: string
  summary: string
  source: string
  configured: Record<string, unknown>
  current_state: Record<string, unknown>
  related_chapters: string[]
}

export interface PlanningRelation {
  id: string
  source: string
  target: string
  label: string
  intensity: number
  chapter_id: string
  description: string
}

export interface PlanningWorkspace {
  schema_version: number
  entities: PlanningEntity[]
  relations: PlanningRelation[]
  timeline: Record<string, unknown>[]
  counts: Record<string, number>
  warnings: string[]
}

export const EMPTY_PLANNING_WORKSPACE: PlanningWorkspace = {
  schema_version: 1,
  entities: [],
  relations: [],
  timeline: [],
  counts: {},
  warnings: [],
}

export const PLANNING_KIND_LABELS: Record<string, string> = {
  outline: '大纲',
  character: '人物',
  location: '地点',
  organization: '组织',
  object: '物品',
  foreshadow: '伏笔',
  rule: '规则',
}

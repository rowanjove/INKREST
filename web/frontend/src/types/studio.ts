export type StudioKanbanColumnId =
  | 'empty'
  | 'planning'
  | 'ready'
  | 'running'
  | 'blocked'
  | 'complete'

export interface StudioKanbanColumn {
  id: StudioKanbanColumnId
  label: string
}

export interface StudioBookSummary {
  id: string
  name: string
  author_label?: string
  genre?: string
  scale: string
  factory_state: StudioKanbanColumnId
  kanban_column: StudioKanbanColumnId
  completed_chapters: number
  target_chapters: number
  planned_chapters: number
  blocked_count: number
  pending_alert_count: number
  risk_level: 'low' | 'medium' | 'high'
  pinned?: boolean
  updated_at?: string
  is_demo?: boolean
}

export interface FactoryStudioDashboard {
  summary: {
    total: number
    running: number
    blocked: number
    ready: number
    complete: number
  }
  columns: StudioKanbanColumn[]
  books_by_column: Record<StudioKanbanColumnId, StudioBookSummary[]>
  books: StudioBookSummary[]
  active_project_id: string | null
}
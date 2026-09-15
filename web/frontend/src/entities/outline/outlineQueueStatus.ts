export interface OutlineQueueRange {
  arc_id?: string | null
  arc_name?: string | null
  brief_count: number
  chapter_min?: number | null
  chapter_max?: number | null
}

export interface OutlineQueueStatus {
  scale?: string | null
  planning_window?: number | null
  target_chapters?: number | null
  macro_arc_count?: number | null
  workspace_arc_count?: number | null
  last_written_chapter?: number | null
  pending_briefs?: number | null
  current_macro_arc?: {
    arc_id?: string | null
    name?: string | null
    chapters?: string | null
  } | null
  brief_ranges?: OutlineQueueRange[]
  arc_queue_stale?: {
    stale?: boolean
    message?: string | null
  } | null
  outline_layer_impl?: string | null
}


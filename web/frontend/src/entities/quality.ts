export interface CalibrationReport {
  status: 'calibrated' | 'uncalibrated' | string
  sample_count: number
  minimum_samples: number
  golden_count: number
  mutation_count: number
  mutation_match_rate: number
  feedback_counts?: Record<string, number>
  errors?: string[]
  mutation_summary?: Record<string, number>
  layer_summary?: Record<string, Record<string, number>>
}

export interface VoiceLabState {
  status: 'calibrated' | 'uncalibrated' | string
  frozen: boolean
  freeze_reason?: string
  state_revision?: number
  profile?: {
    status?: string
    revision?: number
    sample_count?: number
    profile_id?: string
  }
  versions?: Array<{
    revision?: number
    profile_id?: string
    status?: string
    sample_count?: number
    char_count?: number
    is_active?: boolean
  }>
  evidence?: Array<{
    id?: string
    kind?: string
    path?: string
    preview?: string
    sha256?: string
    char_count?: number
  }>
  drift_trend?: Array<{
    chapter_id: string
    status?: string
    score?: number
    deviations?: Record<string, number>
  }>
  feedback?: Array<Record<string, unknown>>
  feedback_count?: number
}

export interface QualityMetrics {
  status: 'calibrated' | 'uncalibrated' | string
  sample_count: number
  minimum_samples: number
  calibration_status?: string
  aggregate: {
    chapter_count: number
    quality_report_count: number
    quality_pass_rate: number | null
    fact_conflict_count: number
    knowledge_boundary_count: number
    expression_repetition_count: number
    rewrite_rounds: number
    quality_error_count: number
    audit_error_count: number
    candidate_feedback_count: number
    pairwise_count: number
    candidate_accept_rate: number | null
    candidate_edit_ratio: number | null
    candidate_false_positive_count?: number
    false_positive_rate?: number | null
    candidate_cost_units?: number
    calibration_false_positive_count?: number
  }
  rows: Array<{
    chapter_id: string
    quality_pass: boolean | null
    quality_score?: number | null
    fact_conflicts: number
    knowledge_boundary_findings: number
    expression_repetitions: number
    rewrite_rounds: number
    candidate_feedback: number
    pairwise_count: number
    candidate_accepts: number
    candidate_edits: number
    candidate_deletes: number
  }>
}

export interface QualityReview {
  chapter_id: string
  document?: {
    revision?: number
    sha256?: string
    char_count?: number
  }
  levels: Record<string, Record<string, unknown>>
  quality: Record<string, any>
  audit: Record<string, any>
  unified_gate: Record<string, any>
  candidate_set?: {
    candidate_set_id?: string
    status?: string
    expires_at?: string
    candidates?: Array<Record<string, any>>
  } | null
  ranked_candidates?: Array<Record<string, any>>
  feedback?: Array<Record<string, any>>
  timeline?: Array<Record<string, any>>
  evidence?: Array<Record<string, any>>
  candidate_policy?: {
    recommend?: boolean
    mode?: string
    score?: number
    reason_codes?: string[]
    report_only?: boolean
  }
}

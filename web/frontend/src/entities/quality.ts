import { QUALITY_CHECK_LABELS } from './production/production'

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
  quality_decision?: {
    status: 'pass' | 'review' | 'blocked' | 'incomplete' | string
    title: string
    message: string
    blocking: boolean
    hard_gate_pass: boolean
    audit_complete: boolean
    keep: boolean
    blocked_by: string[]
    next_action: string
  }
  issues?: Array<{
    code: string
    label: string
    severity: 'error' | 'warning' | string
    score?: number | null
    details?: string[]
    blocking?: boolean
    suggestion?: string
    location?: string
    span?: unknown
  }>
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

export interface L0BlockBanner {
  title: string
  items: string[]
  score: number | null
  keep: boolean
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item || '').trim()).filter(Boolean)
}

export function l0BlockBanner(review: QualityReview | null | undefined): L0BlockBanner | null {
  if (!review) return null
  const guard = (review.quality?.guard_summary || {}) as Record<string, unknown>
  const chapterScore = (review.quality?.chapter_score || {}) as Record<string, unknown>
  const blocked = asStringList(guard.blocked_by)
  const fromScore = asStringList(chapterScore.blocked_by)
  const l0Failed = asStringList((review.levels?.l0 || {}).failed)
  const items = (blocked.length ? blocked : fromScore.length ? fromScore : l0Failed).map(
    (code) => QUALITY_CHECK_LABELS[code] || code.replaceAll('_', ' '),
  )
  if (!items.length) return null
  const rawScore = chapterScore.score
  const score = typeof rawScore === 'number' ? rawScore : rawScore != null ? Number(rawScore) : null
  return {
    title: 'L0 硬门未通过，自动化生产会阻断本章',
    items,
    score: Number.isFinite(score) ? Number(score) : null,
    keep: chapterScore.keep === true,
  }
}

export interface HWEIssueDetail {
  rule_id: string
  family: string
  confidence: number
  start: number
  end: number
  line: number
  paragraph: number
  matched_text: string
  context_before?: string
  context_after?: string
  autofix?: string
  blocking?: boolean
  source?: string
  explainable?: boolean
}

export interface HWEIssue {
  type: string
  issue_layer: 'plan' | 'text' | 'state' | 'risk'
  severity: 'low' | 'medium' | 'high'
  audit_class: string
  text: string
  why: string
  fix: string
  hwe: HWEIssueDetail
}

export interface HWEScores {
  naturalness: number
  rhythm: number
  narrative_trust: number
  voice: number
  freshness: number
  fidelity: number
  template_risk: number
  overall_score: number
}

export interface HWEReport {
  chapter_id?: string | null
  document_revision_id?: string | null
  engine_version: string
  ruleset_version: string
  mode: string
  char_count: number
  scores: HWEScores
  issues: HWEIssue[]
  issue_counts_by_family: Record<string, number>
  issue_counts_by_severity: Record<string, number>
  summary: string
  created_at: string
}

export interface ProtectedSpan {
  kind: string
  value: string
  policy: 'exact' | 'semantic_exact' | 'must_preserve'
  start?: number | null
  end?: number | null
}

export interface FidelityResult {
  passed: boolean
  violations: string[]
  preserved_spans: ProtectedSpan[]
  missing_spans: ProtectedSpan[]
  edit_ratio: number
  length_delta: number
}

export interface PatchPlanItem {
  patch_id: string
  rule_ids: string[]
  family: string
  start: number
  end: number
  radius: 'phrase' | 'sentence' | 'paragraph' | 'dialogue' | 'streak'
  original_text: string
  instruction: string
  risk: 'low' | 'medium' | 'high'
  protected_spans: ProtectedSpan[]
}

export interface HWEPatchCandidate {
  patch_id: string
  rule_ids: string[]
  start: number
  end: number
  original_text: string
  candidate_text: string
  instruction: string
  fidelity: FidelityResult
  utility: number
  quality_gain: number
  diff_unified: string
  status: 'pending' | 'accepted' | 'rejected'
  created_at: string
}



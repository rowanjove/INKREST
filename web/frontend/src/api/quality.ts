import api from './client'
import type {
  CalibrationReport,
  HWEIssue,
  HWEPatchCandidate,
  HWEReport,
  PatchPlanItem,
  QualityMetrics,
  QualityReview,
  VoiceLabState,
} from '../entities/quality'

export const getVoiceLab = () => api.get<VoiceLabState>('/quality/voice-lab')

export const setVoiceLabFrozen = (frozen: boolean, reason = '') =>
  api.post<{ status: string; state: Record<string, unknown>; voice_lab: VoiceLabState }>(
    '/quality/voice-lab/freeze',
    { frozen, reason },
  )

export const recordVoiceFeedback = (feedback: Record<string, unknown>) =>
  api.post<{ status: string; event: Record<string, unknown>; voice_lab: VoiceLabState }>(
    '/quality/voice-lab/feedback',
    feedback,
  )

export const getQualityCalibration = () => api.get<CalibrationReport>('/quality/calibration')

export const saveQualityGolden = (chapters: Array<Record<string, unknown>>, minimum_samples = 20) =>
  api.post<{ status: string; calibration: CalibrationReport }>('/quality/calibration/golden', {
    chapters,
    minimum_samples,
  })

export const runQualityCalibration = () => api.post<CalibrationReport>('/quality/calibration/run')

export const recordCalibrationFeedback = (feedback: Record<string, unknown>) =>
  api.post<{ status: string; event: Record<string, unknown>; calibration: CalibrationReport }>(
    '/quality/calibration/feedback',
    feedback,
  )

export const getQualityMetrics = (minimum_samples = 20) =>
  api.get<QualityMetrics>('/quality/metrics', { params: { minimum_samples } })

export const createQualityBaseline = (minimum_samples = 20) =>
  api.post<QualityMetrics>('/quality/metrics/baseline', { minimum_samples })

export const getQualityReview = (chapterId: string) =>
  api.get<QualityReview>('/quality/review', { params: { chapter_id: chapterId } })

export const adoptCandidateSetCandidate = (
  chapterId: string,
  candidateId: string,
  expectedRevision: number,
  expectedCandidateSetId: string,
) =>
  api.post(`/manuscript/documents/${chapterId}/candidate-set/candidates/${candidateId}/adopt`, {
    expected_revision: expectedRevision,
    expected_candidate_set_id: expectedCandidateSetId,
  })

export const rollbackCandidateSet = (
  chapterId: string,
  timelineId: string,
  expectedCandidateSetId: string,
) =>
  api.post(`/manuscript/documents/${chapterId}/candidate-set/rollback`, {
    timeline_id: timelineId,
    expected_candidate_set_id: expectedCandidateSetId,
  })

export const exportQualityMetrics = (format: 'json' | 'csv' = 'json') =>
  api.get<string>('/quality/metrics/export', { params: { format }, responseType: format === 'csv' ? 'text' : 'json' })

export const getHweReport = (chapterId: string) =>
  api.get<HWEReport>(`/hwe/reports/${chapterId}`)

export const scanHweText = (data: { text?: string; chapter_id?: string; mode?: string }) =>
  api.post<HWEReport>('/hwe/scan', data)

export const listHweRules = (family?: string) =>
  api.get<{ count: number; rules: Array<Record<string, unknown>>; ruleset_version: string }>('/hwe/rules', {
    params: { family },
  })

export const planHwePatches = (data: { text?: string; chapter_id?: string; project_characters?: string[] }) =>
  api.post<PatchPlanItem[]>('/hwe/patch/plan', data)

export const generateHwePatch = (data: { patch: PatchPlanItem; max_edit_ratio?: number }) =>
  api.post<HWEPatchCandidate>('/hwe/patch/generate', data)

export const acceptHwePatch = (data: {
  chapter_id: string
  patch_id: string
  start: number
  end: number
  candidate_text: string
  rule_ids?: string[]
}) => api.post<HWEReport>('/hwe/patches/accept', data)

export const getHweMemoryDiagnostics = (chapterId: string) =>
  api.get<{
    chapter_id: string
    total_extracted_entries: number
    sliding_windows: Array<{
      expression: string
      kind: string
      window_3_count: number
      window_10_count: number
      whole_book_count: number
      is_saturated: boolean
      evidence_chapters: string[]
    }>
    saturated_count: number
    ending_issues: HWEIssue[]
  }>(`/hwe/memory/${chapterId}`)

export const runHweSemanticReview = (data: {
  text?: string
  chapter_id?: string
  pov?: string
  characters?: string[]
  template_risk?: number
  mode?: string
  user_requested?: boolean
}) => api.post<HWEIssue[]>('/hwe/semantic-review', data)

export const previewHwePrompt = (data: {
  chapter_id?: string
  scene_type?: string
  pov?: string
  characters?: string[]
  user_constraints?: string[]
  max_budget?: number
}) =>
  api.post<{
    prompt_block: string
    char_count: number
    budget: number
    within_budget: boolean
  }>('/hwe/prompt-preview', data)

export const resolveHweIssue = (
  issueId: string,
  data: { action: string; rule_id?: string; note?: string }
) => api.post<{ status: string; issue_id: string; action: string }>(`/hwe/issues/${issueId}/resolve`, data)

export const getHwePreferences = () =>
  api.get<{
    project_id: string
    suppressed_rules: string[]
    rule_weights: Record<string, number>
  }>('/hwe/preferences')

export const updateHwePreferences = (data: {
  suppress_rule?: string
  unsuppress_rule?: string
  rule_weights?: Record<string, number>
  reason?: string
}) => api.post('/hwe/preferences', data)

export const runHweEval = () =>
  api.post<{
    benchmark_name: string
    timestamp: string
    engine_version: string
    ruleset_version: string
    metrics: {
      total_cases: number
      positive_cases: number
      negative_cases: number
      true_positives: number
      false_positives: number
      true_negatives: number
      false_negatives: number
      precision: number
      recall: number
      f1_score: number
      false_positive_rate: number
      avg_latency_ms: number
    }
    fpr_target_met: boolean
    results: Array<Record<string, unknown>>
  }>('/hwe/eval/run')

export const getLatestHweEval = () =>
  api.get<{
    benchmark_name: string
    timestamp: string
    metrics: Record<string, unknown>
    fpr_target_met: boolean
  }>('/hwe/eval/latest')

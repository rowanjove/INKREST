import api from './client'
import type { CalibrationReport, QualityMetrics, QualityReview, VoiceLabState } from '../entities/quality'

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

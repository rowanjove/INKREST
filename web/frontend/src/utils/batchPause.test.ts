import { describe, expect, it } from 'vitest'
import {
  formatBatchPauseReason,
  needsRepairBeforeResume,
  productionResumeAction,
} from './batchPause'

describe('batchPause', () => {
  it('treats quality_blocked as repair-first pause', () => {
    expect(needsRepairBeforeResume('quality_blocked')).toBe(true)
    expect(formatBatchPauseReason('quality_blocked')).toBe('门禁阻断')
  })

  it('formats unknown reasons as raw code', () => {
    expect(formatBatchPauseReason('custom')).toBe('custom')
  })

  it('only resumes a genuinely paused production task', () => {
    expect(productionResumeAction('paused')).toBe('resume')
    expect(productionResumeAction('pending')).toBe('observe')
    expect(productionResumeAction('claimed')).toBe('observe')
    expect(productionResumeAction('running')).toBe('observe')
    expect(productionResumeAction('succeeded')).toBe('start')
    expect(productionResumeAction(undefined)).toBe('start')
  })
})

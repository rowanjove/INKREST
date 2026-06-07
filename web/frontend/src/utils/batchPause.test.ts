import { describe, expect, it } from 'vitest'
import { formatBatchPauseReason, needsRepairBeforeResume } from './batchPause'

describe('batchPause', () => {
  it('treats quality_blocked as repair-first pause', () => {
    expect(needsRepairBeforeResume('quality_blocked')).toBe(true)
    expect(formatBatchPauseReason('quality_blocked')).toBe('门禁阻断')
  })

  it('formats unknown reasons as raw code', () => {
    expect(formatBatchPauseReason('custom')).toBe('custom')
  })
})
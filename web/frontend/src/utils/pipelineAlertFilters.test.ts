import { describe, expect, it } from 'vitest'
import {
  canRerunAudit,
  isBatchRetry,
  isExternalPending,
  isQualityBlocked,
  needsRepairActions,
  PENDING_STEP_CARDS,
} from './pipelineAlertFilters'

const gateItem = {
  chapter_id: '001',
  last_stage: 'quality_blocked',
  quality: { blocked_by: ['hook'] },
}

const retryItem = { chapter_id: '002', last_stage: 'batch_retry' }
const externalItem = { chapter_id: '003', last_stage: 'external_review_pending' }

describe('pipelineAlertFilters', () => {
  it('detects quality blocked chapters', () => {
    expect(isQualityBlocked(gateItem)).toBe(true)
    expect(isQualityBlocked(retryItem)).toBe(false)
  })

  it('detects batch retry and external pending', () => {
    expect(isBatchRetry(retryItem)).toBe(true)
    expect(isExternalPending(externalItem)).toBe(true)
  })

  it('aggregates repair actions', () => {
    expect(needsRepairActions(gateItem)).toBe(true)
    expect(needsRepairActions(externalItem)).toBe(true)
    expect(needsRepairActions({ last_stage: 'done' })).toBe(false)
  })

  it('blocks gate rerun for external pending', () => {
    expect(canRerunAudit(externalItem as any)).toBe(false)
    expect(canRerunAudit(gateItem as any)).toBe(true)
  })

  it('defines four pending step cards', () => {
    expect(PENDING_STEP_CARDS).toHaveLength(4)
    expect(PENDING_STEP_CARDS.map((c) => c.id)).toEqual(['gate', 'retry', 'external', 'all'])
  })

  it('filters gate card targets', () => {
    const gateCard = PENDING_STEP_CARDS.find((c) => c.id === 'gate')!
    expect(gateCard.filter(gateItem as any)).toBe(true)
    expect(gateCard.filter(externalItem as any)).toBe(false)
  })
})
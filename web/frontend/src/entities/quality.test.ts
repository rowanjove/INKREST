import { describe, expect, it } from 'vitest'
import { l0BlockBanner, type QualityReview } from './quality'

const review = (overrides: Partial<QualityReview> = {}): QualityReview => ({
  chapter_id: '001',
  levels: {
    l0: { status: 'review', finding_count: 2, failed: ['scene_delta'] },
    l1: { status: 'pass', finding_count: 0, failed: [] },
    l2: { status: 'pass', finding_count: 0, failed: [] },
  },
  quality: {
    overall_score: 42,
    chapter_score: { score: 5.0, keep: false, blocked_by: ['scene_delta'] },
    guard_summary: { overall_status: 'FAIL', blocked_by: ['scene_delta'] },
  },
  audit: {},
  unified_gate: { blocked: true },
  ...overrides,
})

describe('quality center L0 banner', () => {
  it('surfaces blocked_by and chapter score when L0 failed', () => {
    const banner = l0BlockBanner(review())
    expect(banner).not.toBeNull()
    expect(banner?.title).toContain('L0')
    expect(banner?.items).toEqual(['场景推进'])
    expect(banner?.score).toBe(5)
    expect(banner?.keep).toBe(false)
  })

  it('stays quiet when L0 is clean', () => {
    expect(
      l0BlockBanner(
        review({
          levels: {
            l0: { status: 'pass', finding_count: 0, failed: [] },
            l1: { status: 'review', finding_count: 1, failed: ['style'] },
            l2: { status: 'pass', finding_count: 0, failed: [] },
          },
          quality: {
            overall_score: 78,
            chapter_score: { score: 8.2, keep: true, blocked_by: [] },
            guard_summary: { overall_status: 'WARN', blocked_by: [] },
          },
          unified_gate: { blocked: false },
        }),
      ),
    ).toBeNull()
  })
})

import { describe, expect, it } from 'vitest'
import {
  SCALE_OPTIONS,
  designScaleUpperLimit,
  resolveScaleBudget,
  targetChaptersInputMax,
} from './scaleOptions'

describe('scaleOptions budget contract', () => {
  it('keeps epic hard max at 3000', () => {
    expect(targetChaptersInputMax('epic')).toBe(3000)
    expect(resolveScaleBudget('epic', 800).scaleHardMax).toBe(3000)
    expect(resolveScaleBudget('epic', 800).projectSoftTarget).toBe(800)
  })

  it('lets infinite use a 5000 soft target without raising the epic ceiling', () => {
    expect(targetChaptersInputMax('infinite')).toBeGreaterThanOrEqual(5000)
    const budget = resolveScaleBudget('infinite', 5000)
    expect(budget.projectSoftTarget).toBe(5000)
    expect(budget.scaleHardMax).toBe(999999)
    expect(budget.runChapterBudget).toBeLessThan(5000)
  })

  it('exposes the same six scales as the backend', () => {
    expect(SCALE_OPTIONS.map((item) => item.scale)).toEqual([
      'micro',
      'short',
      'medium',
      'long',
      'epic',
      'infinite',
    ])
  })

  it('correctly calculates designScaleUpperLimit for all scale tiers', () => {
    expect(designScaleUpperLimit('micro')).toBe(3)
    expect(designScaleUpperLimit('short')).toBe(20)
    expect(designScaleUpperLimit('medium')).toBe(100)
    expect(designScaleUpperLimit('long')).toBe(500)
    expect(designScaleUpperLimit('epic')).toBe(3000)
    expect(designScaleUpperLimit('infinite')).toBe(1200)
    // Custom target larger than scale limit
    expect(designScaleUpperLimit('medium', 120)).toBe(120)
    // Fallback when scale is missing
    expect(designScaleUpperLimit(undefined, 35)).toBe(35)
    expect(designScaleUpperLimit(undefined, 0)).toBe(20)
  })
})

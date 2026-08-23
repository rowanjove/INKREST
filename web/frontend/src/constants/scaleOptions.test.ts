import { describe, expect, it } from 'vitest'
import {
  SCALE_OPTIONS,
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
})

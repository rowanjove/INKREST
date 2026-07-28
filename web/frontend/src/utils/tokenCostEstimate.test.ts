import { describe, expect, it } from 'vitest'
import {
  estimateBatchTokenCost,
  formatCnyEstimate,
  formatCnyYuan,
  formatTokenEstimate,
  resolveDailyModelPricePer1k,
  resolveDailyModelRef,
  TOKENS_PER_CHAPTER_ESTIMATE,
} from './tokenCostEstimate'

describe('tokenCostEstimate', () => {
  it('resolves daily model ref from config', () => {
    expect(resolveDailyModelRef({ llm: { daily_model_id: 'm1' } })).toBe('m1')
    expect(resolveDailyModelRef({ llm: { default: { model_ref: 'm2' } } })).toBe('m2')
  })

  it('uses model blended price when available', () => {
    const { pricePer1k, modelLabel } = resolveDailyModelPricePer1k(
      { llm: { daily_model_id: 'a' } },
      [{ id: 'a', name: 'Test', blended_price_per_1k_cny: 0.05 }],
    )
    expect(pricePer1k).toBe(0.05)
    expect(modelLabel).toBe('Test')
  })

  it('falls back to default blended price', () => {
    const { pricePer1k } = resolveDailyModelPricePer1k({ llm: {} }, [])
    expect(pricePer1k).toBeGreaterThan(0)
  })

  it('formats token counts', () => {
    expect(formatTokenEstimate(0)).toBe('—')
    expect(formatTokenEstimate(1500)).toContain('k')
    expect(formatTokenEstimate(2_000_000)).toContain('M')
  })

  it('formats cny in yuan', () => {
    expect(formatCnyYuan(0)).toBe('—')
    expect(formatCnyYuan(2.4)).toBe('¥2.40')
    expect(formatCnyYuan(0.309)).toBe('¥0.31')
    expect(formatCnyYuan(0.005)).toBe('¥0.0050')
  })

  it('formats cny estimates with prefix', () => {
    expect(formatCnyEstimate(0)).toBe('—')
    expect(formatCnyEstimate(2.4)).toBe('约 ¥2.40')
    expect(formatCnyEstimate(0.05)).toBe('约 ¥0.05')
  })

  it('estimates batch cost from chapters', () => {
    const est = estimateBatchTokenCost(2, 0.01)
    expect(est.tokens).toBe(2 * TOKENS_PER_CHAPTER_ESTIMATE)
    expect(est.cny).toBeGreaterThan(0)
    expect(est.chapters).toBe(2)
  })

  it('returns empty estimate for zero chapters', () => {
    const est = estimateBatchTokenCost(0, 0.01)
    expect(est.tokens).toBe(0)
    expect(est.label).toBe('—')
  })
})
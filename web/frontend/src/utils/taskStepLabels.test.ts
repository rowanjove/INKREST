import { describe, expect, it } from 'vitest'
import { formatTaskStep } from './taskStepLabels'

describe('formatTaskStep', () => {
  it('maps known pipeline steps to Chinese labels', () => {
    expect(formatTaskStep('writer')).toBe('AI 写作正文初稿')
    expect(formatTaskStep('quality_guard')).toBe('质量门禁检查')
  })

  it('falls back for empty or unknown steps', () => {
    expect(formatTaskStep()).toBe('运行中')
    expect(formatTaskStep('custom_step')).toBe('custom_step')
  })
})
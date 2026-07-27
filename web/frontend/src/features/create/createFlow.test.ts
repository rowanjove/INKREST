import { describe, expect, it } from 'vitest'
import {
  CREATE_STEPS,
  canEnterDetails,
  nextCreateStep,
  sourceMode,
  sourceRequiresModel,
} from './createFlow'

describe('four-step creation flow', () => {
  it('keeps the approved four stages in order', () => {
    expect(CREATE_STEPS).toEqual(['工作方式', '素材来源', '写作规格', '确认建档'])
  })

  it('only blocks sources that actually require a model', () => {
    expect(canEnterDetails('quick', false)).toBe(true)
    expect(canEnterDetails('template', false)).toBe(true)
    expect(canEnterDetails('ai', false)).toBe(false)
    expect(canEnterDetails('parse', false)).toBe(false)
    expect(sourceRequiresModel('ai')).toBe(true)
  })

  it('embeds templates in quick creation instead of a top-level page', () => {
    expect(sourceMode('template')).toBe('quick')
  })

  it('does not enter confirmation until a valid draft exists', () => {
    expect(nextCreateStep(2, { source: 'quick', modelReady: true, hasDraft: false })).toBe(2)
    expect(nextCreateStep(2, { source: 'quick', modelReady: true, hasDraft: true })).toBe(3)
  })
})

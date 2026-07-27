import { describe, expect, it } from 'vitest'

import { formatWordCount, preflightTone } from './publishing'

describe('publishing domain helpers', () => {
  it('formats publication counts for compact summary cards', () => {
    expect(formatWordCount(9876)).toBe('9,876')
    expect(formatWordCount(12_500)).toBe('1.3 万')
    expect(formatWordCount(220_000)).toBe('22 万')
  })

  it('maps preflight severity to stable tones', () => {
    expect(preflightTone('blocking')).toBe('danger')
    expect(preflightTone('warning')).toBe('warning')
    expect(preflightTone('ready')).toBe('success')
  })
})

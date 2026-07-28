import { describe, expect, it } from 'vitest'
import { isMessageBoxDismissal } from './elementPlusServices'

describe('isMessageBoxDismissal', () => {
  it.each(['cancel', 'close'])('accepts the %s action string', (action) => {
    expect(isMessageBoxDismissal(action)).toBe(true)
  })

  it.each([{ action: 'cancel' }, { action: 'close' }])(
    'accepts an action-bearing rejection object',
    (reason) => {
      expect(isMessageBoxDismissal(reason)).toBe(true)
    },
  )

  it('does not hide actual failures', () => {
    expect(isMessageBoxDismissal(new Error('request failed'))).toBe(false)
    expect(isMessageBoxDismissal({ action: 'confirm' })).toBe(false)
  })
})

import { describe, expect, it } from 'vitest'
import {
  SAVE_STATUS_LABELS,
  createAiEditIntent,
  saveStatusTone,
} from './manuscript'

describe('manuscript state contracts', () => {
  it('creates an explicit AI intent before any request is made', () => {
    const intent = createAiEditIntent('polish', '003', {
      text: '雨落在窗沿。',
      from: 4,
      to: 11,
      x: 300,
      y: 180,
    })

    expect(intent.label).toBe('润色')
    expect(intent.chapterId).toBe('003')
    expect(intent.instruction).toContain('画面感')
    expect(intent.selection.text).toBe('雨落在窗沿。')
  })

  it('keeps conflict and unsaved states visible', () => {
    expect(SAVE_STATUS_LABELS.conflict).toBe('发现版本冲突')
    expect(saveStatusTone('conflict')).toBe('warning')
    expect(saveStatusTone('error')).toBe('danger')
    expect(saveStatusTone('saved')).toBe('success')
  })
})

import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  applyBatchFormDefaults,
  batchFormStorageKey,
  cancelBatchRunMessage,
  computeRoundProgress,
  loadSavedBatchForm,
  mergeBatchForm,
  saveBatchForm,
} from './batchRunForm'

describe('batchRunForm', () => {
  const memory = new Map<string, string>()

  beforeEach(() => {
    memory.clear()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => memory.get(key) ?? null,
      setItem: (key: string, value: string) => {
        memory.set(key, value)
      },
      removeItem: (key: string) => {
        memory.delete(key)
      },
      clear: () => memory.clear(),
    })
  })

  it('builds storage key per project', () => {
    expect(batchFormStorageKey('proj_a')).toBe('inkrest_batch_form_proj_a')
  })

  it('round-trips saved form', () => {
    saveBatchForm('p1', { target_chapters: 7, autopilot: true })
    expect(loadSavedBatchForm('p1')).toEqual({ target_chapters: 7, autopilot: true })
  })

  it('rejects invalid saved target', () => {
    localStorage.setItem(batchFormStorageKey('p1'), JSON.stringify({ target_chapters: 0 }))
    expect(loadSavedBatchForm('p1')).toBeNull()
  })

  it('applies scale defaults for long works', () => {
    expect(applyBatchFormDefaults('long', 12)).toEqual({ target_chapters: 12, autopilot: true })
    expect(applyBatchFormDefaults('long', 8)).toEqual({ target_chapters: 8, autopilot: true })
    expect(applyBatchFormDefaults('micro', 3)).toEqual({ target_chapters: 3, autopilot: false })
  })

  it('merges saved form within cap', () => {
    const merged = mergeBatchForm({ target_chapters: 10, autopilot: true }, { target_chapters: 99, autopilot: false }, 5)
    expect(merged).toEqual({ target_chapters: 5, autopilot: false })
  })

  it('computes round progress label', () => {
    const p = computeRoundProgress({ roundTarget: 3, startChapterCount: 2, currentChapterCount: 4 })
    expect(p.written).toBe(2)
    expect(p.label).toContain('已写 2 章')
  })

  it('maps cancel messages by phase', () => {
    expect(cancelBatchRunMessage('opening', false)).toContain('开书状态')
    expect(cancelBatchRunMessage('submitting_continue', true)).toContain('取消请求')
  })
})
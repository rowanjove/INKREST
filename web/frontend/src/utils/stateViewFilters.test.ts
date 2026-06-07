import { describe, expect, it } from 'vitest'
import { matchesChapterRange, maxChapterFromState } from './stateViewFilters'

describe('stateViewFilters', () => {
  describe('matchesChapterRange', () => {
    const range: [number, number] = [2, 5]

    it('includes items without chapter_id', () => {
      expect(matchesChapterRange({}, range)).toBe(true)
      expect(matchesChapterRange(null, range)).toBe(true)
    })

    it('includes items with non-numeric chapter_id', () => {
      expect(matchesChapterRange({ chapter_id: 'abc' }, range)).toBe(true)
    })

    it('filters by numeric chapter range', () => {
      expect(matchesChapterRange({ chapter_id: '1' }, range)).toBe(false)
      expect(matchesChapterRange({ chapter_id: '3' }, range)).toBe(true)
      expect(matchesChapterRange({ chapter_id: '5' }, range)).toBe(true)
      expect(matchesChapterRange({ chapter_id: '6' }, range)).toBe(false)
    })
  })

  describe('maxChapterFromState', () => {
    it('returns 1 for empty state', () => {
      expect(maxChapterFromState(null)).toBe(1)
      expect(maxChapterFromState({})).toBe(1)
    })

    it('finds max chapter across foreshadows, hooks, and events', () => {
      const state = {
        foreshadows: [{ chapter_id: '3' }, { chapter_id: '7' }],
        hooks: [{ chapter_id: '5' }],
        events: [{ chapter_id: '12' }, { chapter_id: '2' }],
      }
      expect(maxChapterFromState(state)).toBe(12)
    })
  })
})
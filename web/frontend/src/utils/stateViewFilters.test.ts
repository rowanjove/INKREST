import { describe, expect, it } from 'vitest'
import {
  buildChronicleTimeline,
  matchesChapterRange,
  maxChapterFromState,
  paginateTimelineItems,
} from './stateViewFilters'

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

  describe('buildChronicleTimeline', () => {
    it('filters by chapter range, sorts by chapter, and merges matching timeline records by id', () => {
      const result = buildChronicleTimeline({
        source: {
          events: [
            { id: 'e3', chapter_id: '3', summary: 'third' },
            { id: 'e1', chapter_id: '1', summary: 'outside' },
            { id: 'e2', chapter_id: '2', summary: 'second' },
          ],
          foreshadows: [
            { id: 'f1', chapter_id: '2', title: 'seed', status: 'open' },
            { id: 'f2', chapter_id: '6', title: 'outside' },
          ],
          hooks: [{ id: 'h1', chapter_id: '3', content: 'old hook' }],
        },
        timeline: {
          nodes: [
            { id: 'n5', chapter_id: '5', label: 'later' },
            { id: 'n2', chapter_id: '2', label: 'earlier' },
            { id: 'n9', chapter_id: '9', label: 'outside' },
          ],
          foreshadows: [{ id: 'f1', chapter_id: '2', status: 'resolved' }],
          hooks: [
            { id: 'h1', chapter_id: '3', content: 'merged hook', pressure_level: 'high' },
            { id: 'h2', chapter_id: '4', content: 'new hook' },
          ],
        },
        range: [2, 5],
      })

      expect(result.events.map((item) => item.id)).toEqual(['e2', 'e3'])
      expect(result.nodes.map((item) => item.id)).toEqual(['n2', 'n5'])
      expect(result.foreshadows).toEqual([
        { id: 'f1', chapter_id: '2', title: 'seed', status: 'resolved' },
      ])
      expect(result.hooks).toEqual([
        { id: 'h1', chapter_id: '3', content: 'merged hook', pressure_level: 'high' },
        { id: 'h2', chapter_id: '4', content: 'new hook' },
      ])
    })
  })

  describe('paginateTimelineItems', () => {
    it('returns the requested one-based page without mutating items', () => {
      const items = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }]

      expect(paginateTimelineItems(items, 2, 2)).toEqual([{ id: 3 }, { id: 4 }])
      expect(items).toHaveLength(4)
    })
  })
})

import { describe, expect, it } from 'vitest'
import { buildMinimalOutline } from './createOutline'

const base = {
  name: '测试书',
  description: '',
  genre: '',
  channel: 'general',
  target_chapters: 200,
  scale: 'long',
  scale_label: '长篇小说',
  target_chars_per_chapter: [2000, 3000],
  composition: {
    channel: 'general',
    theme: 'dushi',
    theme_label: '都市',
    mechanisms: [],
    cool_points: [],
  },
}

describe('buildMinimalOutline', () => {
  it('keeps a long-form quick-create outline as a non-runnable draft', () => {
    const outline = buildMinimalOutline(base)
    expect(outline.genre_positioning).toBe('都市')
    expect(outline.planning_status).toBe('draft')
    expect(outline.macro_outline).toEqual([])
  })

  it('keeps the documented direct-run skeleton for short fiction', () => {
    const outline = buildMinimalOutline({
      ...base,
      scale: 'short',
      scale_label: '短篇',
      target_chapters: 10,
    })
    expect(outline.planning_status).toBe('ready')
    expect(outline.macro_outline).toHaveLength(1)
  })
})

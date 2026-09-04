import { describe, expect, it } from 'vitest'

import {
  ADVANCED_PROJECT_NAV_ITEMS,
  GLOBAL_NAV_ITEMS,
  PROJECT_NAV_ITEMS,
  routeFallback,
} from './navigation'
import { appScrollBehavior } from './routeMeta'

describe('V2 navigation contract', () => {
  it('keeps the global shell focused on four entry points', () => {
    expect(GLOBAL_NAV_ITEMS.map((item) => item.label)).toEqual([
      '书库',
      '新建作品',
      '设置',
      '扩展',
    ])
  })

  it('keeps six core centers in project navigation with quality directly accessible', () => {
    expect(PROJECT_NAV_ITEMS.map((item) => item.label)).toEqual([
      '概览',
      '策划',
      '正文',
      '生产',
      '质量',
      '发布',
    ])
    expect(new Set(PROJECT_NAV_ITEMS.map((item) => item.path)).size).toBe(6)
    expect(ADVANCED_PROJECT_NAV_ITEMS).toEqual([])
  })

  it('only redirects project-scoped routes when no project is hydrated', () => {
    expect(routeFallback('project', false)).toEqual({ name: 'library' })
    expect(routeFallback('project', true)).toBe(true)
    expect(routeFallback('global', false)).toBe(true)
    expect(routeFallback('pet', false)).toBe(true)
  })

  it('restores history, honors hashes, and otherwise returns to the top', () => {
    const plain = { hash: '' } as never
    const hashed = { hash: '#embedding-config' } as never
    const saved = { left: 0, top: 240 }

    expect(appScrollBehavior(plain, plain, saved)).toEqual(saved)
    expect(appScrollBehavior(hashed, plain, null)).toEqual({
      el: '#embedding-config',
      behavior: 'smooth',
    })
    expect(appScrollBehavior(plain, plain, null)).toEqual({ left: 0, top: 0 })
  })
})

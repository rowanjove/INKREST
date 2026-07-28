import { describe, expect, it } from 'vitest'
import {
  channelLabel,
  formatCardDate,
  formatCardTime,
  formatWords,
  getCoverClass,
  lastEditLabel,
  lastEditTitle,
} from './libraryFormatters'
import type { Project } from '../stores/project'

const baseProject = (overrides: Partial<Project> = {}): Project =>
  ({
    id: 'p1',
    name: '测试书',
    ...overrides,
  }) as Project

describe('libraryFormatters', () => {
  it('maps channel ids to labels', () => {
    expect(channelLabel('male')).toBe('男频')
    expect(channelLabel('female')).toBe('女频')
    expect(channelLabel('unknown')).toBe('')
  })

  it('formats word counts', () => {
    expect(formatWords(0)).toBe('0字')
    expect(formatWords(9999)).toBe('9999字')
    expect(formatWords(12000)).toBe('1.2万字')
  })

  it('picks cover class by channel', () => {
    expect(getCoverClass('male')).toBe('cover-male')
    expect(getCoverClass()).toBe('cover-general')
  })

  it('formats card date and time from activity_at', () => {
    const project = baseProject({ activity_at: '2026-06-07T15:30:00.000Z' })
    expect(formatCardDate(project.activity_at)).toMatch(/2026年/)
    expect(formatCardTime(project.activity_at)).toMatch(/^\d{2}:\d{2}$/)
    expect(lastEditLabel(project)).toMatch(/2026年/)
    expect(lastEditTitle(project)).toContain('更新')
  })
})
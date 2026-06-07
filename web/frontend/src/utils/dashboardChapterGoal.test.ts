import { describe, expect, it } from 'vitest'
import { buildChapterGoalTemplate } from './dashboardChapterGoal'

describe('buildChapterGoalTemplate', () => {
  it('builds goal from outline theme and protagonist', () => {
    const goal = buildChapterGoalTemplate({
      chapterId: '003',
      outline: {
        protagonist: { name: '林默' },
        conflict: '宗门试炼',
        core_theme: '逆天改命',
      },
      outlineTheme: '逆天改命',
    })
    expect(goal).toContain('第 3 章')
    expect(goal).toContain('林默')
    expect(goal).toContain('宗门试炼')
  })

  it('uses chapter id label when not numeric', () => {
    const goal = buildChapterGoalTemplate({
      chapterId: 'prologue',
      outline: null,
      outlineTheme: '',
      projectName: '测试书',
    })
    expect(goal.startsWith('prologue：')).toBe(true)
    expect(goal).toContain('测试书')
  })
})
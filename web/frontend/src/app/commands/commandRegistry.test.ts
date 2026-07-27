import { describe, expect, it } from 'vitest'

import type { SnapshotAction } from '../../entities/project/projectSnapshot'
import {
  buildNavigationCommands,
  commandFromSnapshotAction,
  searchCommands,
} from './commandRegistry'

describe('command registry', () => {
  it('offers only global destinations without a project', () => {
    const commands = buildNavigationCommands(false)

    expect(commands.map((command) => command.label)).toEqual([
      '书库',
      '新建作品',
      '设置',
      '扩展',
    ])
  })

  it('adds all five project centers and keeps settings searchable', () => {
    const commands = buildNavigationCommands(true)

    expect(commands.filter((command) => command.group === '项目').map((command) => command.label))
      .toEqual(['概览', '策划', '正文', '生产', '发布'])
    expect(searchCommands(commands, '模型')).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ path: '/config#model-library', label: '模型与提供方' }),
      ]),
    )
  })

  it('ranks exact prefix matches before loose keyword matches', () => {
    const commands = buildNavigationCommands(true)
    const results = searchCommands(commands, '正文')

    expect(results[0].label).toBe('正文')
  })

  it('turns generation intents into navigation-only confirmation commands', () => {
    const action: SnapshotAction = {
      id: 'continue_writing',
      label: '继续创作',
      kind: 'intent',
      target: 'novel_continue',
      enabled: true,
    }

    expect(commandFromSnapshotAction(action)).toMatchObject({
      path: '/workspace?intent=novel_continue',
      executeMode: 'navigate',
    })
  })
})

import { describe, expect, it } from 'vitest'

import type { SnapshotAction } from '../../entities/project/projectSnapshot'
import {
  buildNavigationCommands,
  commandFromSnapshotAction,
  commandsFromPluginNavigation,
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

  it('keeps core centers and makes the quality center searchable', () => {
    const commands = buildNavigationCommands(true)

    expect(commands.filter((command) => command.group === '项目').map((command) => command.label))
      .toEqual(['概览', '策划', '正文', '生产', '质量', '发布'])
    expect(searchCommands(commands, '质量')[0]).toMatchObject({ path: '/quality' })
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
      path: '/production?intent=novel_continue&confirm=1',
      executeMode: 'navigate',
    })
  })

  it('converts plugin navigation contributions into searchable commands', () => {
    const pluginCommands = commandsFromPluginNavigation([
      {
        id: 'story-tools:radar',
        plugin_id: 'story-tools',
        plugin_name: '故事工具箱',
        contribution_id: 'radar',
        title: '伏笔雷达',
        surface: 'project_sidebar',
        icon: 'radar',
        view: 'radar-view',
        path: '/extensions/project/story-tools/radar-view',
        order: 100,
        default_visibility: 'visible',
        requires: [],
      },
    ])

    expect(pluginCommands).toHaveLength(1)
    expect(pluginCommands[0]).toMatchObject({
      id: 'plugin-nav-story-tools:radar',
      label: '伏笔雷达',
      group: '项目',
      path: '/extensions/project/story-tools/radar-view',
    })
    const searchRes = searchCommands(pluginCommands, '伏笔')
    expect(searchRes[0].path).toBe('/extensions/project/story-tools/radar-view')
  })
})

import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { usePluginNavigationStore } from './pluginNavigation'
import type { PluginNavigationContribution } from '../entities/plugin/pluginNavigation'

describe('pluginNavigation store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    if (typeof localStorage !== 'undefined' && localStorage.clear) {
      localStorage.clear()
    }
  })

  it('partitions items into active and overflow based on limits', () => {
    const store = usePluginNavigationStore()

    // 5 project items (limit is 4)
    const projectItems: PluginNavigationContribution[] = [1, 2, 3, 4, 5].map((i) => ({
      id: `p${i}:view`,
      plugin_id: `p${i}`,
      plugin_name: `插件${i}`,
      contribution_id: 'view',
      title: `项目入口${i}`,
      surface: 'project_sidebar',
      icon: 'radar',
      view: 'view',
      path: `/extensions/project/p${i}/view`,
      order: i * 10,
      default_visibility: 'visible',
      requires: [],
    }))

    store.projectItems = projectItems

    expect(store.visibleProjectItems).toHaveLength(5)
    expect(store.activeProjectItems).toHaveLength(4)
    expect(store.overflowProjectItems).toHaveLength(1)
    expect(store.overflowProjectItems[0].id).toBe('p5:view')
  })

  it('pinning places an item first, hiding excludes it', () => {
    const store = usePluginNavigationStore()

    store.libraryItems = [
      {
        id: 'lib:normal',
        plugin_id: 'lib',
        plugin_name: '库插件',
        contribution_id: 'normal',
        title: '普通模板',
        surface: 'library_sidebar',
        icon: 'collection',
        view: 'normal',
        path: '/extensions/library/lib/normal',
        order: 100,
        default_visibility: 'visible',
        requires: [],
      },
      {
        id: 'lib:pinned',
        plugin_id: 'lib',
        plugin_name: '库插件',
        contribution_id: 'pinned',
        title: '置顶模板',
        surface: 'library_sidebar',
        icon: 'collection',
        view: 'pinned',
        path: '/extensions/library/lib/pinned',
        order: 200,
        default_visibility: 'visible',
        requires: [],
      },
    ]

    // Default order: normal (order 100) before pinned (order 200)
    expect(store.visibleLibraryItems[0].id).toBe('lib:normal')

    // Pin the second item
    store.togglePin('lib:pinned')
    expect(store.isPinned('lib:pinned')).toBe(true)
    expect(store.visibleLibraryItems[0].id).toBe('lib:pinned')

    // Hide normal
    store.toggleHide('lib:normal')
    expect(store.isHidden('lib:normal')).toBe(true)
    expect(store.visibleLibraryItems).toHaveLength(1)
    expect(store.visibleLibraryItems[0].id).toBe('lib:pinned')
  })

  it('increments context revision on project switch', () => {
    const store = usePluginNavigationStore()
    expect(store.contextRevision).toBe(1)
    store.incrementRevision()
    expect(store.contextRevision).toBe(2)
  })
})

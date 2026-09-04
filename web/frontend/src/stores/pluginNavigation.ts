import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchPluginNavigation } from '../api'
import type { PluginNavigationContribution } from '../entities/plugin/pluginNavigation'

const STORAGE_KEY_PINNED = 'inkrest_plugin_nav_pinned_v1'
const STORAGE_KEY_HIDDEN = 'inkrest_plugin_nav_hidden_v1'

const LIBRARY_PINNED_LIMIT = 6
const PROJECT_PINNED_LIMIT = 4

function loadStoredIds(key: string): string[] {
  if (typeof window === 'undefined' || !window.localStorage) return []
  try {
    const raw = window.localStorage.getItem(key)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveStoredIds(key: string, ids: string[]): void {
  if (typeof window === 'undefined' || !window.localStorage) return
  try {
    window.localStorage.setItem(key, JSON.stringify(ids))
  } catch {
    // ignore storage write failures
  }
}

export const usePluginNavigationStore = defineStore('pluginNavigation', () => {
  const libraryItems = ref<PluginNavigationContribution[]>([])
  const projectItems = ref<PluginNavigationContribution[]>([])
  const pinnedIds = ref<string[]>(loadStoredIds(STORAGE_KEY_PINNED))
  const hiddenIds = ref<string[]>(loadStoredIds(STORAGE_KEY_HIDDEN))
  const status = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const contextRevision = ref<number>(1)

  const isPinned = (id: string) => pinnedIds.value.includes(id)
  const isHidden = (id: string) => hiddenIds.value.includes(id)

  const togglePin = (id: string) => {
    if (pinnedIds.value.includes(id)) {
      pinnedIds.value = pinnedIds.value.filter((x) => x !== id)
    } else {
      pinnedIds.value = [...pinnedIds.value, id]
    }
    saveStoredIds(STORAGE_KEY_PINNED, pinnedIds.value)
  }

  const toggleHide = (id: string) => {
    if (hiddenIds.value.includes(id)) {
      hiddenIds.value = hiddenIds.value.filter((x) => x !== id)
    } else {
      hiddenIds.value = [...hiddenIds.value, id]
    }
    saveStoredIds(STORAGE_KEY_HIDDEN, hiddenIds.value)
  }

  const sortItems = (items: PluginNavigationContribution[]) => {
    return [...items].sort((a, b) => {
      const aPinned = isPinned(a.id) ? 0 : 1
      const bPinned = isPinned(b.id) ? 0 : 1
      if (aPinned !== bPinned) return aPinned - bPinned
      if (a.order !== b.order) return a.order - b.order
      return a.id.localeCompare(b.id)
    })
  }

  const visibleLibraryItems = computed(() =>
    sortItems(libraryItems.value.filter((item) => !isHidden(item.id))),
  )

  const visibleProjectItems = computed(() =>
    sortItems(projectItems.value.filter((item) => !isHidden(item.id))),
  )

  const activeLibraryItems = computed(() =>
    visibleLibraryItems.value.slice(0, LIBRARY_PINNED_LIMIT),
  )

  const overflowLibraryItems = computed(() =>
    visibleLibraryItems.value.slice(LIBRARY_PINNED_LIMIT),
  )

  const activeProjectItems = computed(() =>
    visibleProjectItems.value.slice(0, PROJECT_PINNED_LIMIT),
  )

  const overflowProjectItems = computed(() =>
    visibleProjectItems.value.slice(PROJECT_PINNED_LIMIT),
  )

  const fetchNavigation = async () => {
    status.value = 'loading'
    try {
      const res = await fetchPluginNavigation()
      const data = res.data || {}
      libraryItems.value = data.library_sidebar || []
      projectItems.value = data.project_sidebar || []
      status.value = 'ready'
    } catch {
      status.value = 'error'
    }
  }

  const incrementRevision = () => {
    contextRevision.value += 1
  }

  return {
    libraryItems,
    projectItems,
    pinnedIds,
    hiddenIds,
    status,
    contextRevision,
    isPinned,
    isHidden,
    togglePin,
    toggleHide,
    visibleLibraryItems,
    visibleProjectItems,
    activeLibraryItems,
    overflowLibraryItems,
    activeProjectItems,
    overflowProjectItems,
    fetchNavigation,
    incrementRevision,
  }
})

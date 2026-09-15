import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSidebarQuickActionsStore } from './sidebarQuickActions'

class MockStorage {
  private store: Record<string, string> = {}
  getItem(key: string) { return this.store[key] ?? null }
  setItem(key: string, val: string) { this.store[key] = val }
  removeItem(key: string) { delete this.store[key] }
  clear() { this.store = {} }
}

describe('sidebarQuickActions store', () => {
  beforeEach(() => {
    ;(globalThis as any).localStorage = new MockStorage()
    setActivePinia(createPinia())
  })

  it('initializes with default settings', () => {
    const store = useSidebarQuickActionsStore()
    expect(store.showLabels).toBe(true)
    expect(store.maxSlots).toBe(3)
    expect(store.enabledIds).toEqual(['plugins', 'shanshan'])
    expect(store.enabledActions.map((a) => a.id)).toEqual(['plugins', 'shanshan'])
  })

  it('respects slot limit of 3 when labels are shown', () => {
    const store = useSidebarQuickActionsStore()
    expect(store.enableAction('diagnostics')).toBe(true)
    expect(store.enabledIds.length).toBe(3)
    // 4th should fail
    expect(store.enableAction('command')).toBe(false)
    expect(store.enabledIds.length).toBe(3)
  })

  it('respects slot limit of 5 when labels are hidden', () => {
    const store = useSidebarQuickActionsStore()
    store.setShowLabels(false)
    expect(store.maxSlots).toBe(5)
    expect(store.enableAction('diagnostics')).toBe(true)
    expect(store.enableAction('command')).toBe(true)
    expect(store.enabledIds.length).toBe(4)
  })

  it('truncates excess items when switching from icon-only to labels', () => {
    const store = useSidebarQuickActionsStore()
    store.setShowLabels(false)
    store.enableAction('diagnostics')
    store.enableAction('command')
    expect(store.enabledIds.length).toBe(4)

    store.setShowLabels(true)
    expect(store.enabledIds.length).toBe(3)
    expect(store.enabledIds).toEqual(['plugins', 'shanshan', 'diagnostics'])
  })

  it('moves actions left and right', () => {
    const store = useSidebarQuickActionsStore()
    expect(store.enabledIds).toEqual(['plugins', 'shanshan'])
    store.moveAction(0, 1)
    expect(store.enabledIds).toEqual(['shanshan', 'plugins'])
  })

  it('removes actions and disables already enabled ones', () => {
    const store = useSidebarQuickActionsStore()
    expect(store.disableAction('shanshan')).toBe(true)
    expect(store.enabledIds).toEqual(['plugins'])
    expect(store.disableAction('shanshan')).toBe(false)
  })
})

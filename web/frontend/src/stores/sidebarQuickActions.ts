import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'

export type SidebarActionId = 'plugins' | 'inspiration' | 'shanshan' | 'diagnostics' | 'command'

export interface SidebarActionDefinition {
  id: SidebarActionId
  label: string
  icon: string
  description: string
  route?: string
  isRoute?: boolean
}

export const SIDEBAR_AVAILABLE_ACTIONS: readonly SidebarActionDefinition[] = [
  {
    id: 'plugins',
    label: '插件',
    icon: 'Cpu',
    description: '快速前往插件中心，管理已安装插件与权限',
    route: '/plugins',
    isRoute: true,
  },
  {
    id: 'inspiration',
    label: '灵感',
    icon: 'Opportunity',
    description: '进入灵感工坊，构思套路组合与故事蓝图',
    route: '/inspiration',
    isRoute: true,
  },
  {
    id: 'shanshan',
    label: '山山',
    icon: 'Avatar',
    description: '唤出驻场桌面小编辑「山山」助手',
  },
  {
    id: 'diagnostics',
    label: '诊断',
    icon: 'Monitor',
    description: '查看后台运行状态与系统诊断面板',
  },
  {
    id: 'command',
    label: '命令',
    icon: 'Search',
    description: '呼出全局搜索与命令面板 (Ctrl+K)',
  },
]

const STORAGE_KEY = 'inkrest_sidebar_quick_actions'

export interface SidebarQuickActionsState {
  showLabels: boolean
  enabledIds: SidebarActionId[]
}

const DEFAULT_STATE: SidebarQuickActionsState = {
  showLabels: true,
  enabledIds: ['plugins', 'shanshan'],
}

function getStorage(): Storage | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage
    }
    if (typeof globalThis !== 'undefined' && (globalThis as any).localStorage) {
      return (globalThis as any).localStorage
    }
  } catch {
    // 忽略安全沙箱可能抛出的异常
  }
  return null
}

function loadPersistedState(): SidebarQuickActionsState {
  try {
    const storage = getStorage()
    const raw = storage ? storage.getItem(STORAGE_KEY) : null
    if (!raw) return { ...DEFAULT_STATE, enabledIds: [...DEFAULT_STATE.enabledIds] }
    const parsed = JSON.parse(raw)
    const validIds = new Set(SIDEBAR_AVAILABLE_ACTIONS.map((a) => a.id))
    const showLabels = typeof parsed.showLabels === 'boolean' ? parsed.showLabels : true
    const max = showLabels ? 3 : 5

    let enabledIds: SidebarActionId[] = []
    if (Array.isArray(parsed.enabledIds)) {
      enabledIds = parsed.enabledIds.filter((id: unknown): id is SidebarActionId =>
        typeof id === 'string' && validIds.has(id as SidebarActionId),
      )
    }
    if (enabledIds.length === 0) {
      enabledIds = ['plugins', 'shanshan']
    }
    if (enabledIds.length > max) {
      enabledIds = enabledIds.slice(0, max)
    }
    return { showLabels, enabledIds }
  } catch {
    return { ...DEFAULT_STATE, enabledIds: [...DEFAULT_STATE.enabledIds] }
  }
}

export const useSidebarQuickActionsStore = defineStore('sidebarQuickActions', () => {
  const initialState = loadPersistedState()
  const showLabels = ref(initialState.showLabels)
  const enabledIds = ref<SidebarActionId[]>(initialState.enabledIds)

  const maxSlots = computed(() => (showLabels.value ? 3 : 5))

  const enabledActions = computed(() => {
    const map = new Map(SIDEBAR_AVAILABLE_ACTIONS.map((item) => [item.id, item]))
    return enabledIds.value
      .map((id) => map.get(id))
      .filter((item): item is SidebarActionDefinition => Boolean(item))
  })

  const availableActions = computed(() => {
    const enabledSet = new Set(enabledIds.value)
    return SIDEBAR_AVAILABLE_ACTIONS.filter((item) => !enabledSet.has(item.id))
  })

  function persist() {
    try {
      const storage = getStorage()
      if (storage) {
        storage.setItem(
          STORAGE_KEY,
          JSON.stringify({
            showLabels: showLabels.value,
            enabledIds: enabledIds.value,
          }),
        )
      }
    } catch {
      // 容错处理
    }
  }

  watch([showLabels, enabledIds], persist, { deep: true })

  function setShowLabels(val: boolean) {
    showLabels.value = val
    const limit = val ? 3 : 5
    if (enabledIds.value.length > limit) {
      enabledIds.value = enabledIds.value.slice(0, limit)
    }
  }

  function moveAction(fromIndex: number, toIndex: number) {
    if (
      fromIndex < 0 ||
      fromIndex >= enabledIds.value.length ||
      toIndex < 0 ||
      toIndex >= enabledIds.value.length
    ) {
      return
    }
    const copy = [...enabledIds.value]
    const [moved] = copy.splice(fromIndex, 1)
    copy.splice(toIndex, 0, moved)
    enabledIds.value = copy
  }

  function enableAction(id: SidebarActionId) {
    if (enabledIds.value.includes(id)) return false
    if (enabledIds.value.length >= maxSlots.value) return false
    enabledIds.value.push(id)
    return true
  }

  function disableAction(id: SidebarActionId) {
    const index = enabledIds.value.indexOf(id)
    if (index !== -1) {
      enabledIds.value.splice(index, 1)
      return true
    }
    return false
  }

  function resetToDefault() {
    showLabels.value = DEFAULT_STATE.showLabels
    enabledIds.value = [...DEFAULT_STATE.enabledIds]
  }

  return {
    showLabels,
    enabledIds,
    maxSlots,
    enabledActions,
    availableActions,
    allActions: SIDEBAR_AVAILABLE_ACTIONS,
    setShowLabels,
    moveAction,
    enableAction,
    disableAction,
    resetToDefault,
  }
})

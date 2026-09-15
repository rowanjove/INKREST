import { computed, getCurrentInstance, onMounted, onUnmounted, ref } from 'vue'

// Legacy ids are accepted in read-only snapshots during migration; settings
// writes are normalized by the Electron main process to `github`.
export type UpdateSourceId = 'github' | 'ghproxy' | 'mirror' | 'custom'

export interface UpdateSourceDefinition {
  id: UpdateSourceId
  name: string
  badge: string
  description: string
  hint: string
}

export const UPDATE_SOURCES: UpdateSourceDefinition[] = [
  {
    id: 'github',
    name: 'GitHub 官方源',
    badge: '官方推荐',
    description: '仅从项目 GitHub Releases 官方通道检查版本',
    hint: '安装包请从官方发布页手动下载',
  },
]

const defaultSettings: ElectronUpdateSettings = {
  autoCheck: true,
  autoDownload: false,
  sourceId: 'github',
  customSourceUrl: '',
  checkPrerelease: false,
  lastCheckedAt: null,
}

const defaultStatus: ElectronUpdaterStatusSnapshot = {
  state: 'idle',
  currentVersion: '2.0.2',
  sourceId: 'github',
  effectiveFeedUrl: 'https://github.com/rowanjove/inkrest/releases/latest/download/',
  isPortable: false,
}

function getElectronAPI(): ElectronAPI | undefined {
  if (typeof window !== 'undefined') {
    return window.electronAPI
  }
  return undefined
}

export function useUpdater() {
  const settings = ref<ElectronUpdateSettings>({ ...defaultSettings })
  const status = ref<ElectronUpdaterStatusSnapshot>({ ...defaultStatus })
  const isSaving = ref(false)
  const settingsError = ref<string | null>(null)

  const isChecking = computed(() => status.value.state === 'checking')
  const hasUpdate = computed(() => status.value.state === 'available')
  const isNotAvailable = computed(() => status.value.state === 'not-available')
  const hasError = computed(() => status.value.state === 'error')

  let unsubscribeStatus: (() => void) | null = null

  const fetchSettings = async () => {
    const api = getElectronAPI()
    if (!api?.getUpdateSettings) return
    try {
      settings.value = await api.getUpdateSettings()
    } catch (err) {
      console.warn('[useUpdater] Failed to load update settings:', err)
    }
  }

  const fetchStatus = async () => {
    const api = getElectronAPI()
    if (!api?.getUpdateStatus) return
    try {
      status.value = await api.getUpdateStatus()
    } catch (err) {
      console.warn('[useUpdater] Failed to load update status:', err)
    }
  }

  const updateSettings = async (patch: Partial<ElectronUpdateSettings>) => {
    isSaving.value = true
    settingsError.value = null
    try {
      const api = getElectronAPI()
      if (api?.updateUpdateSettings) {
        settings.value = await api.updateUpdateSettings(patch)
      } else {
        settings.value = { ...settings.value, ...patch }
      }
    } catch (err) {
      settingsError.value = err instanceof Error ? err.message : String(err)
    } finally {
      isSaving.value = false
    }
  }

  const checkForUpdates = async () => {
    if (isChecking.value) return
    const api = getElectronAPI()
    if (api?.checkForUpdates) {
      await api.checkForUpdates()
    } else {
      // Dev / browser mockup
      status.value = { ...status.value, state: 'checking', error: undefined }
      setTimeout(() => {
        status.value = {
          ...status.value,
          state: 'not-available',
          lastError: undefined,
        } as any
      }, 1200)
    }
  }

  const openReleasePage = (url?: string) => {
    const api = getElectronAPI()
    if (api?.openReleasePage) {
      api.openReleasePage(url)
    } else if (typeof window !== 'undefined') {
      // Keep browser-mode previews within the same official release page
      // allowlist as the Electron main process.
      const official = 'https://github.com/rowanjove/inkrest/releases'
      const candidate = typeof url === 'string' && /^https:\/\/github\.com\/rowanjove\/inkrest\/releases(?:\/|$)/u.test(url)
        ? url
        : official
      window.open(candidate, '_blank', 'noopener,noreferrer')
    }
  }

  if (getCurrentInstance()) {
    onMounted(() => {
      void fetchSettings()
      void fetchStatus()
      const api = getElectronAPI()
      if (api?.onUpdateStatus) {
        unsubscribeStatus = api.onUpdateStatus((nextStatus) => {
          status.value = nextStatus
          if (nextStatus.sourceId) {
            settings.value.sourceId = nextStatus.sourceId
          }
        })
      }
    })

    onUnmounted(() => {
      if (unsubscribeStatus) {
        unsubscribeStatus()
        unsubscribeStatus = null
      }
    })
  }

  return {
    settings,
    status,
    isSaving,
    settingsError,
    isChecking,
    hasUpdate,
    isNotAvailable,
    hasError,
    fetchSettings,
    fetchStatus,
    updateSettings,
    checkForUpdates,
    openReleasePage,
  }
}

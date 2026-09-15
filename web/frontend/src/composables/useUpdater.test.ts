import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useUpdater, UPDATE_SOURCES } from './useUpdater'

describe('useUpdater composable', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal('window', {})
  })

  it('exposes defined update sources with proper labels and hints', () => {
    expect(UPDATE_SOURCES).toHaveLength(1)
    expect(UPDATE_SOURCES.map((s) => s.id)).toEqual([
      'github',
    ])
    expect(UPDATE_SOURCES[0].name).toContain('官方源')
  })

  it('initializes with default settings and idle status in web environment', () => {
    const { settings, status, isChecking, hasUpdate } = useUpdater()
    expect(settings.value.autoCheck).toBe(true)
    expect(settings.value.autoDownload).toBe(false)
    expect(settings.value.sourceId).toBe('github')
    expect(status.value.state).toBe('idle')
    expect(isChecking.value).toBe(false)
    expect(hasUpdate.value).toBe(false)
  })

  it('interacts with electronAPI when available', async () => {
    const mockGetSettings = vi.fn().mockResolvedValue({
      autoCheck: false,
      autoDownload: true,
      sourceId: 'github',
      customSourceUrl: '',
      checkPrerelease: false,
      lastCheckedAt: 1700000000000,
    })
    const mockUpdateSettings = vi.fn().mockImplementation(async (patch) => ({
      autoCheck: false,
      autoDownload: true,
      sourceId: 'github',
      customSourceUrl: '',
      checkPrerelease: false,
      lastCheckedAt: 1700000000000,
      ...patch,
    }))
    const mockGetStatus = vi.fn().mockResolvedValue({
      state: 'available',
      currentVersion: '2.0.2',
      updateInfo: {
        version: '2.0.3',
        releaseNotes: '新版本发布说明',
      },
      sourceId: 'ghproxy',
      effectiveFeedUrl: 'https://github.com/rowanjove/inkrest/releases/latest/download/',
      isPortable: false,
    })
    const mockCheckForUpdates = vi.fn().mockResolvedValue(undefined)
    ;(window as any).electronAPI = {
      getUpdateSettings: mockGetSettings,
      updateUpdateSettings: mockUpdateSettings,
      getUpdateStatus: mockGetStatus,
      checkForUpdates: mockCheckForUpdates,
      onUpdateStatus: vi.fn().mockReturnValue(() => {}),
    }

    const updater = useUpdater()

    await updater.fetchSettings()
    expect(mockGetSettings).toHaveBeenCalled()
    expect(updater.settings.value.sourceId).toBe('github')
    expect(updater.settings.value.autoCheck).toBe(false)

    await updater.fetchStatus()
    expect(mockGetStatus).toHaveBeenCalled()
    expect(updater.hasUpdate.value).toBe(true)
    expect(updater.status.value.updateInfo?.version).toBe('2.0.3')

    await updater.updateSettings({ sourceId: 'github' })
    expect(mockUpdateSettings).toHaveBeenCalledWith({ sourceId: 'github' })
    expect(updater.settings.value.sourceId).toBe('github')

    await updater.checkForUpdates()
    expect(mockCheckForUpdates).toHaveBeenCalled()

  })
})

import { BrowserWindow, app, shell } from 'electron'
import {
  type UpdateSettings,
  type UpdateSourceId,
  normalizeUpdateSettings,
  readUpdateSettings,
  writeUpdateSettings,
  resolveEffectiveUpdateFeedUrl,
  OFFICIAL_RELEASE_PAGE_URL,
  isAllowedReleasePageUrl,
} from './update-settings'

export type UpdaterState =
  | 'idle'
  | 'checking'
  | 'available'
  | 'not-available'
  | 'downloading'
  | 'downloaded'
  | 'error'

export interface UpdateInfoPayload {
  version: string
  releaseDate?: string
  releaseNotes?: string
  files?: Array<{ url?: string; size?: number }>
}

export interface UpdateProgressPayload {
  percent: number
  bytesPerSecond: number
  transferred: number
  total: number
}

export interface UpdaterStatusSnapshot {
  state: UpdaterState
  currentVersion: string
  updateInfo?: UpdateInfoPayload
  progress?: UpdateProgressPayload
  error?: string
  sourceId: UpdateSourceId
  effectiveFeedUrl: string
  isPortable: boolean
}

let autoUpdaterInstance: any = null

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  autoUpdaterInstance = require('electron-updater').autoUpdater
} catch (err) {
  console.warn('[Updater] electron-updater not available:', err)
}

export class UpdaterManager {
  private mainWindow: BrowserWindow | null = null
  private settings: UpdateSettings
  private state: UpdaterState = 'idle'
  private currentUpdateInfo?: UpdateInfoPayload
  private currentProgress?: UpdateProgressPayload
  private lastError?: string
  private startupTimer: NodeJS.Timeout | null = null
  private readonly isPortable: boolean
  private listeners: Array<{ event: string; handler: (...args: any[]) => void }> = []
  private initialized = false

  constructor() {
    this.settings = readUpdateSettings()
    this.isPortable = Boolean(process.env.PORTABLE_EXECUTABLE_DIR)
  }

  public init(mainWindow: BrowserWindow): void {
    this.mainWindow = mainWindow
    this.initialized = false
    if (!autoUpdaterInstance) {
      console.warn('[Updater] electron-updater is not loaded. Online updater disabled.')
      return
    }
    this.initialized = true

    // Configure autoUpdater basic settings
    autoUpdaterInstance.autoDownload = false
    // In-app installation is disabled until a publisher signature can be
    // verified independently of the update feed.  Users are directed to the
    // official release page instead.
    autoUpdaterInstance.autoInstallOnAppQuit = false
    autoUpdaterInstance.disableWebInstaller = true

    // Enable updater in dev mode if explicitly requested or needed
    if (!app.isPackaged) {
      autoUpdaterInstance.forceDevUpdateConfig = true
    }

    this.setupListeners()
    this.applySourceConfig()
    this.scheduleStartupCheck()
  }

  public setMainWindow(win: BrowserWindow | null): void {
    this.mainWindow = win
  }

  private setupListeners(): void {
    if (!autoUpdaterInstance || this.listeners.length > 0) return

    this.addListener('checking-for-update', () => {
      console.log('[Updater] Checking for updates...')
      this.state = 'checking'
      this.lastError = undefined
      this.broadcastStatus()
    })

    this.addListener('update-available', (info: any) => {
      console.log('[Updater] Update available:', info?.version)
      this.state = 'available'
      this.currentUpdateInfo = {
        version: String(info?.version || ''),
        releaseDate: info?.releaseDate ? String(info.releaseDate) : undefined,
        releaseNotes: typeof info?.releaseNotes === 'string' ? info.releaseNotes : undefined,
        files: Array.isArray(info?.files)
          ? info.files.map((f: any) => ({ url: f.url, size: f.size }))
          : undefined,
      }
      this.settings.lastCheckedAt = Date.now()
      writeUpdateSettings(this.settings)
      this.broadcastStatus()

    })

    this.addListener('update-not-available', (info: any) => {
      console.log('[Updater] Up to date (latest:', info?.version, ')')
      this.state = 'not-available'
      this.settings.lastCheckedAt = Date.now()
      writeUpdateSettings(this.settings)
      this.broadcastStatus()
    })

    this.addListener('download-progress', (progress: any) => {
      this.state = 'downloading'
      this.currentProgress = {
        percent: Math.round((progress.percent || 0) * 10) / 10,
        bytesPerSecond: Math.round(progress.bytesPerSecond || 0),
        transferred: Math.round(progress.transferred || 0),
        total: Math.round(progress.total || 0),
      }
      this.broadcastStatus()
    })

    this.addListener('update-downloaded', (info: any) => {
      console.log('[Updater] Update downloaded:', info?.version)
      this.state = 'downloaded'
      this.broadcastStatus()
    })

    this.addListener('error', (err: any) => {
      const errMsg = err?.message || String(err)
      console.error('[Updater] Error:', errMsg)
      this.state = 'error'
      this.lastError = this.formatErrorMessage(errMsg)
      this.broadcastStatus()
    })
  }

  private addListener(event: string, handler: (...args: any[]) => void): void {
    autoUpdaterInstance.on(event, handler)
    this.listeners.push({ event, handler })
  }

  private scheduleStartupCheck(): void {
    if (this.startupTimer) {
      clearTimeout(this.startupTimer)
      this.startupTimer = null
    }
    if (!this.initialized || !autoUpdaterInstance || !this.settings.autoCheck) return

    this.startupTimer = setTimeout(() => {
      this.startupTimer = null
      console.log('[Updater] Triggering background startup update check...')
      this.checkForUpdates(false).catch((err) => {
        console.warn('[Updater] Background update check failed:', err)
      })
    }, 15000)
  }

  private formatErrorMessage(raw: string): string {
    if (/timeout|ETIMEDOUT|ESOCKETTIMEDOUT/i.test(raw)) {
      return '连接 GitHub 官方更新服务器超时，请检查网络设置后重试。'
    }
    if (/ECONNRESET|ECONNREFUSED|ENOTFOUND/i.test(raw)) {
      return '无法连接 GitHub 官方更新服务器，请检查网络设置后重试。'
    }
    if (/404|Cannot find latest/i.test(raw)) {
      return '更新源上暂未找到版本清单 (latest.yml)，请核对更新源地址。'
    }
    return `检查更新失败: ${raw}`
  }

  public applySourceConfig(): void {
    if (!autoUpdaterInstance) return

    const feedUrl = resolveEffectiveUpdateFeedUrl(this.settings)
    console.log('[Updater] Applying feed URL:', feedUrl)

    try {
      autoUpdaterInstance.setFeedURL({
        provider: 'generic',
        url: feedUrl,
      })
      autoUpdaterInstance.allowPrerelease = this.settings.checkPrerelease
    } catch (err) {
      console.error('[Updater] Failed to setFeedURL:', err)
    }
  }

  public async checkForUpdates(manual = true): Promise<void> {
    if (!autoUpdaterInstance) {
      this.state = 'error'
      this.lastError = '更新模块不可用（缺少 electron-updater 依赖）'
      this.broadcastStatus()
      return
    }

    try {
      this.state = 'checking'
      this.lastError = undefined
      this.broadcastStatus()
      this.applySourceConfig()
      await autoUpdaterInstance.checkForUpdates()
    } catch (err: any) {
      if (manual) {
        this.state = 'error'
        this.lastError = this.formatErrorMessage(err?.message || String(err))
        this.broadcastStatus()
      } else {
        console.warn('[Updater] Background check failed silently:', err?.message)
      }
    }
  }

  public async downloadUpdate(): Promise<void> {
    // The feed is intentionally check-only: a generic feed or unsigned
    // installer must never become an in-app code execution path.
    this.state = 'error'
    this.lastError = '为安全起见，应用内安装已禁用，请前往 GitHub 官方发布页手动下载。'
    this.broadcastStatus()
  }

  public quitAndInstall(): void {
    console.warn('[Updater] In-app installation is disabled; use the official release page.')
  }

  public openReleasePage(customUrl?: string): void {
    const url = isAllowedReleasePageUrl(customUrl) ? customUrl : OFFICIAL_RELEASE_PAGE_URL
    void shell.openExternal(url).catch((err) => {
      console.error('[Updater] Failed to open external URL:', err)
    })
  }

  public getSettings(): UpdateSettings {
    return { ...this.settings }
  }

  public updateSettings(patch: Partial<UpdateSettings>): UpdateSettings {
    this.settings = normalizeUpdateSettings({ ...this.settings, ...patch })
    writeUpdateSettings(this.settings)
    this.applySourceConfig()
    this.scheduleStartupCheck()
    this.broadcastStatus()
    return { ...this.settings }
  }

  public getStatus(): UpdaterStatusSnapshot {
    return {
      state: this.state,
      currentVersion: app.getVersion(),
      updateInfo: this.currentUpdateInfo,
      progress: this.currentProgress,
      error: this.lastError,
      sourceId: this.settings.sourceId,
      effectiveFeedUrl: resolveEffectiveUpdateFeedUrl(this.settings),
      isPortable: this.isPortable,
    }
  }

  public broadcastStatus(): void {
    if (!this.mainWindow || this.mainWindow.isDestroyed()) return
    this.mainWindow.webContents.send('updater:status', this.getStatus())
  }

  public destroy(): void {
    this.initialized = false
    if (this.startupTimer) {
      clearTimeout(this.startupTimer)
      this.startupTimer = null
    }
    if (autoUpdaterInstance) {
      for (const { event, handler } of this.listeners) {
        autoUpdaterInstance.removeListener(event, handler)
      }
    }
    this.listeners = []
    this.mainWindow = null
  }
}


export const updaterManager = new UpdaterManager()

export function initAutoUpdater(mainWindow: BrowserWindow): void {
  updaterManager.init(mainWindow)
}

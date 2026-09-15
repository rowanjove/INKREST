import { app } from 'electron'
import fs from 'fs'
import path from 'path'

/**
 * The updater deliberately has one trusted channel.  Generic feeds and
 * third-party proxies cannot provide the publisher/signature boundary needed
 * for unattended installation.
 */
// Keep legacy identifiers readable for migration/API compatibility. Runtime
// normalization and IPC validation only ever permit the trusted `github`
// channel below.
export type UpdateSourceId = 'github' | 'ghproxy' | 'mirror' | 'custom'

export interface UpdateSourceOption {
  id: UpdateSourceId
  name: string
  description: string
  url: string
}

export const OFFICIAL_REPO_OWNER = 'rowanjove'
export const OFFICIAL_REPO_NAME = 'inkrest'
export const OFFICIAL_RELEASE_URL = `https://github.com/${OFFICIAL_REPO_OWNER}/${OFFICIAL_REPO_NAME}/releases/latest/download/`
export const OFFICIAL_RELEASE_PAGE_URL = `https://github.com/${OFFICIAL_REPO_OWNER}/${OFFICIAL_REPO_NAME}/releases`
export const OFFICIAL_RELEASE_HOSTS: ReadonlySet<string> = new Set(['github.com'])

export function isAllowedReleasePageUrl(rawUrl: unknown): rawUrl is string {
  if (typeof rawUrl !== 'string') return false
  try {
    const url = new URL(rawUrl)
    return url.protocol === 'https:'
      && url.username === ''
      && url.password === ''
      && OFFICIAL_RELEASE_HOSTS.has(url.hostname)
      && (
        url.pathname === `/${OFFICIAL_REPO_OWNER}/${OFFICIAL_REPO_NAME}/releases`
        || url.pathname.startsWith(`/${OFFICIAL_REPO_OWNER}/${OFFICIAL_REPO_NAME}/releases/`)
      )
  } catch {
    return false
  }
}

export const BUILTIN_UPDATE_SOURCES: Record<'github', UpdateSourceOption> = {
  github: {
    id: 'github',
    name: '官方源 (GitHub Releases)',
    description: '仅从项目 GitHub Releases 官方通道检查版本',
    url: OFFICIAL_RELEASE_URL,
  },
}

export interface UpdateSettings {
  autoCheck: boolean
  autoDownload: boolean
  sourceId: UpdateSourceId
  customSourceUrl: string
  checkPrerelease: boolean
  lastCheckedAt: number | null
}

export const DEFAULT_UPDATE_SETTINGS: UpdateSettings = {
  autoCheck: true,
  autoDownload: false,
  sourceId: 'github',
  customSourceUrl: '',
  checkPrerelease: false,
  lastCheckedAt: null,
}

export function updateSettingsPath(): string {
  return path.join(app.getPath('userData'), 'update-settings.json')
}

export function normalizeUpdateSettings(input: Partial<UpdateSettings> = {}): UpdateSettings {
  // Older settings may contain a removed proxy/custom source.  Migrate them
  // to the only trusted channel instead of applying the persisted URL.
  const sourceId: UpdateSourceId = 'github'
  const customSourceUrl = ''

  const lastCheckedAt =
    typeof input.lastCheckedAt === 'number' && Number.isFinite(input.lastCheckedAt) && input.lastCheckedAt > 0
      ? Math.round(input.lastCheckedAt)
      : null

  return {
    autoCheck: typeof input.autoCheck === 'boolean' ? input.autoCheck : DEFAULT_UPDATE_SETTINGS.autoCheck,
    // In-app installation is intentionally disabled until a publisher
    // signature can be verified independently of the feed.
    autoDownload: false,
    sourceId,
    customSourceUrl,
    checkPrerelease: typeof input.checkPrerelease === 'boolean' ? input.checkPrerelease : DEFAULT_UPDATE_SETTINGS.checkPrerelease,
    lastCheckedAt,
  }
}

export function readUpdateSettings(): UpdateSettings {
  const filePath = updateSettingsPath()
  try {
    if (!fs.existsSync(filePath)) return { ...DEFAULT_UPDATE_SETTINGS }
    const content = fs.readFileSync(filePath, 'utf-8')
    const parsed = JSON.parse(content)
    const normalized = normalizeUpdateSettings(parsed)
    // Persist the migration so removed proxy/custom values cannot remain in
    // the user settings file and be accidentally consumed by an older build.
    if (
      typeof parsed === 'object' && parsed !== null
      && (
        (parsed as Record<string, unknown>).sourceId !== 'github'
        || (parsed as Record<string, unknown>).customSourceUrl !== ''
        || (parsed as Record<string, unknown>).autoDownload !== false
      )
    ) {
      writeUpdateSettings(normalized)
    }
    return normalized
  } catch (err) {
    console.warn('[Updater] Failed to read update settings, falling back to default:', err)
    return { ...DEFAULT_UPDATE_SETTINGS }
  }
}

export function writeUpdateSettings(settings: UpdateSettings): void {
  const filePath = updateSettingsPath()
  try {
    const dir = path.dirname(filePath)
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    fs.writeFileSync(filePath, JSON.stringify(settings, null, 2), 'utf-8')
  } catch (err) {
    console.error('[Updater] Failed to write update settings:', err)
  }
}

export function resolveEffectiveUpdateFeedUrl(settings: UpdateSettings): string {
  // Do not let persisted or caller-provided settings select a generic feed.
  return BUILTIN_UPDATE_SOURCES.github.url
}

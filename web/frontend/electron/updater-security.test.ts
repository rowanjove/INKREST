import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { parseUpdateSettingsPatch, validateUpdateSourceUrl } from './security'
import {
  normalizeUpdateSettings,
  resolveEffectiveUpdateFeedUrl,
  BUILTIN_UPDATE_SOURCES,
  OFFICIAL_RELEASE_URL,
  isAllowedReleasePageUrl,
  type UpdateSettings,
} from './updater/update-settings'

describe('Updater security and settings', () => {
  describe('validateUpdateSourceUrl', () => {
    it('rejects all custom feeds, including empty and HTTP URLs', () => {
      expect(() => validateUpdateSourceUrl('https://updates.example.com/releases/')).toThrow(
        'custom update source URLs are disabled',
      )
      expect(() => validateUpdateSourceUrl('http://192.168.1.100:8080/updates')).toThrow()
      expect(() => validateUpdateSourceUrl('')).toThrow()
      expect(() => validateUpdateSourceUrl('   ')).toThrow()
    })

    it('rejects unsupported protocols and credential leaks', () => {
      expect(() => validateUpdateSourceUrl('file:///C:/secret.txt')).toThrow()
      expect(() => validateUpdateSourceUrl('javascript:alert(1)')).toThrow()
      expect(() => validateUpdateSourceUrl('ftp://example.com/update')).toThrow()
      expect(() => validateUpdateSourceUrl('https://user:secret@example.com/updates')).toThrow(
        'must not contain authentication credentials',
      )
      expect(() => validateUpdateSourceUrl('not-a-valid-url')).toThrow()
      expect(() => validateUpdateSourceUrl(123 as any)).toThrow()
    })
  })

  describe('parseUpdateSettingsPatch', () => {
    it('accepts valid partial settings', () => {
      const patch = parseUpdateSettingsPatch({
        autoCheck: false,
        sourceId: 'github',
      })
      expect(patch).toEqual({
        autoCheck: false,
        sourceId: 'github',
      })
    })

    it('rejects unknown keys and invalid types', () => {
      expect(() =>
        parseUpdateSettingsPatch({
          autoCheck: 'false',
        }),
      ).toThrow('autoCheck must be a boolean')

      expect(() => parseUpdateSettingsPatch({ sourceId: 'ghproxy' })).toThrow(
        'third-party and custom feeds are disabled',
      )

      expect(() => parseUpdateSettingsPatch({ customSourceUrl: '' })).toThrow(
        'custom update source URLs are disabled',
      )
      expect(() => parseUpdateSettingsPatch({ autoDownload: true })).toThrow(
        'autoDownload is disabled',
      )

      expect(() =>
        parseUpdateSettingsPatch({
          arbitraryKey: 'bad',
        }),
      ).toThrow('unknown update setting field')

      expect(() => parseUpdateSettingsPatch(null)).toThrow('must be an object')
    })
  })

  describe('resolveEffectiveUpdateFeedUrl', () => {
    it('resolves official github url', () => {
      const settings: UpdateSettings = {
        autoCheck: true,
        autoDownload: false,
        sourceId: 'github',
        customSourceUrl: '',
        checkPrerelease: false,
        lastCheckedAt: null,
      }
      expect(resolveEffectiveUpdateFeedUrl(settings)).toBe(OFFICIAL_RELEASE_URL)
    })

    it('always resolves the official URL for legacy source values', () => {
      const settings: UpdateSettings = {
        autoCheck: true,
        autoDownload: false,
        sourceId: 'github',
        customSourceUrl: '',
        checkPrerelease: false,
        lastCheckedAt: null,
      }
      expect(resolveEffectiveUpdateFeedUrl({ ...settings, sourceId: 'ghproxy' as any })).toBe(OFFICIAL_RELEASE_URL)
    })

    it('does not apply a persisted custom source', () => {
      const settings: UpdateSettings = {
        autoCheck: true,
        autoDownload: false,
        sourceId: 'custom' as any,
        customSourceUrl: 'https://cdn.example.com/desktop-update',
        checkPrerelease: false,
        lastCheckedAt: null,
      }
      expect(resolveEffectiveUpdateFeedUrl(settings)).toBe(OFFICIAL_RELEASE_URL)
    })

    it('normalizes missing or corrupted settings', () => {
      const normalized = normalizeUpdateSettings({
        autoCheck: false,
        sourceId: 'invalid' as any,
      })
      expect(normalized.autoCheck).toBe(false)
      expect(normalized.sourceId).toBe('github')
      expect(normalized.autoDownload).toBe(false)
      expect(normalized.customSourceUrl).toBe('')
    })
  })

  describe('official release page allowlist', () => {
    it('allows only the official GitHub repository release pages', () => {
      expect(isAllowedReleasePageUrl('https://github.com/rowanjove/inkrest/releases')).toBe(true)
      expect(isAllowedReleasePageUrl('https://github.com/rowanjove/inkrest/releases/tag/v2.0.2')).toBe(true)
      expect(isAllowedReleasePageUrl('https://evil.example/rowanjove/inkrest/releases')).toBe(false)
      expect(isAllowedReleasePageUrl('https://github.com/other/repo/releases')).toBe(false)
      expect(isAllowedReleasePageUrl('http://github.com/rowanjove/inkrest/releases')).toBe(false)
      expect(isAllowedReleasePageUrl('javascript:alert(1)')).toBe(false)
    })
  })

  it('renders release notes as escaped text, including hostile event attributes', () => {
    const source = readFileSync(
      join(process.cwd(), 'src', 'components', 'SoftwareUpdateConfig.vue'),
      'utf8',
    )
    expect(source).not.toContain('v-html="status.updateInfo.releaseNotes"')
    expect(source).toContain('<div class="notes-content">{{ status.updateInfo.releaseNotes }}</div>')
    expect(source).toMatch(/<div class="notes-content">\{\{\s*status\.updateInfo\.releaseNotes\s*\}\}<\/div>/u)
    expect(source).not.toMatch(/v-html\s*=\s*['"][^'"]*releaseNotes/u)
    // A release-note payload such as <img src=x onerror=alert(1)> therefore
    // travels through Vue's escaped text interpolation, never raw HTML.
  })
})

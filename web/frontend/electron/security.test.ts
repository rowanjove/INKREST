import { describe, expect, it } from 'vitest'

import {
  appOrigins,
  assertTrustedSenderUrl,
  isAllowedAppUrl,
  isAllowedExternalUrl,
  parseMoveDelta,
  parsePetSettingsPatch,
  parseRoute,
  parseWindowBounds,
} from './security'

describe('Electron security boundary', () => {
  const origins = appOrigins(false, 8123)

  it('allows only the local application origin', () => {
    expect(isAllowedAppUrl('http://127.0.0.1:8123/workspace', origins)).toBe(true)
    expect(isAllowedAppUrl('http://127.0.0.1:8124/workspace', origins)).toBe(false)
    expect(isAllowedAppUrl('https://evil.example/', origins)).toBe(false)
    expect(isAllowedAppUrl('http://user@127.0.0.1:8123/', origins)).toBe(false)
  })

  it('allows only credential-free HTTPS external links', () => {
    const externalHosts = new Set(['docs.example'])
    expect(isAllowedExternalUrl('https://docs.example/guide', externalHosts)).toBe(true)
    expect(isAllowedExternalUrl('https://other.example/', externalHosts)).toBe(false)
    expect(
      isAllowedExternalUrl('https://user@docs.example/guide', externalHosts),
    ).toBe(false)
    expect(isAllowedExternalUrl('http://docs.example/guide', externalHosts)).toBe(false)
    expect(isAllowedExternalUrl('file:///C:/secret.txt', externalHosts)).toBe(false)
  })

  it('rejects untrusted IPC sender URLs', () => {
    expect(() =>
      assertTrustedSenderUrl('http://127.0.0.1:8123/workspace', origins),
    ).not.toThrow()
    expect(() =>
      assertTrustedSenderUrl('https://evil.example/', origins),
    ).toThrow('Untrusted IPC sender')
  })

  it('validates internal navigation routes', () => {
    expect(parseRoute('/monitor?tab=tasks')).toBe('/monitor?tab=tasks')
    expect(() => parseRoute('https://evil.example/')).toThrow()
    expect(() => parseRoute('//evil.example/path')).toThrow()
    expect(() => parseRoute('/ok\r\nbad')).toThrow()
  })

  it('validates window bounds and movement deltas', () => {
    expect(parseWindowBounds({ x: 10.4, y: -2, width: 320, height: 180 })).toEqual({
      x: 10.4,
      y: -2,
      width: 320,
      height: 180,
    })
    expect(parseMoveDelta({ x: -30, y: 12 })).toEqual({ x: -30, y: 12 })
    expect(() => parseWindowBounds({ x: Number.NaN, y: 1 })).toThrow()
    expect(() => parseWindowBounds({ x: 1, y: 2, width: -1 })).toThrow()
    expect(() => parseWindowBounds({ x: 1, y: 2, extra: true })).toThrow()
    expect(() => parseMoveDelta({ x: 5000, y: 0 })).toThrow()
    expect(() => parseMoveDelta({ x: 1, y: 2, extra: true })).toThrow()
  })

  it('accepts only known, typed pet setting fields', () => {
    expect(
      parsePetSettingsPatch({
        enabled: false,
        size: 200,
        position: { x: 10, y: 20 },
        petId: 'shanshan',
      }),
    ).toEqual({
      enabled: false,
      size: 200,
      position: { x: 10, y: 20 },
      petId: 'shanshan',
    })
    expect(() => parsePetSettingsPatch({ unexpected: true })).toThrow()
    expect(() => parsePetSettingsPatch({ enabled: 'yes' })).toThrow()
    expect(() => parsePetSettingsPatch({ petId: '../pet' })).toThrow()
  })
})

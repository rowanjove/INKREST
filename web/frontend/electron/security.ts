import type { PetSettings } from './pet-settings'

export interface WindowBounds {
  x: number
  y: number
  width?: number
  height?: number
}

export interface MoveDelta {
  x: number
  y: number
}

export type BackendState = 'online' | 'offline' | 'restarting'

export interface BackendStatusSnapshot {
  state: BackendState
}

const BOOLEAN_SETTING_KEYS = [
  'enabled',
  'showOnStartup',
  'alwaysOnTop',
  'notifyOnTaskComplete',
  'notifyOnTaskError',
] as const

const PET_SETTING_KEYS = new Set<string>([
  ...BOOLEAN_SETTING_KEYS,
  'size',
  'position',
  'petId',
])

function recordValue(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`)
  }
  return value as Record<string, unknown>
}

function finiteNumber(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new TypeError(`${label} must be a finite number`)
  }
  return value
}

function assertKnownKeys(
  input: Record<string, unknown>,
  allowedKeys: ReadonlySet<string>,
  label: string,
): void {
  for (const key of Object.keys(input)) {
    if (!allowedKeys.has(key)) {
      throw new TypeError(`unknown ${label} field: ${key}`)
    }
  }
}

export function appOrigins(isDev: boolean, apiPort: number): ReadonlySet<string> {
  if (!Number.isInteger(apiPort) || apiPort < 1 || apiPort > 65535) {
    throw new RangeError('apiPort must be a valid TCP port')
  }
  const origins = new Set<string>([`http://127.0.0.1:${apiPort}`])
  if (isDev) {
    origins.add('http://localhost:5173')
    origins.add('http://127.0.0.1:5173')
  }
  return origins
}

export function isAllowedAppUrl(
  rawUrl: string,
  origins: ReadonlySet<string>,
): boolean {
  try {
    const url = new URL(rawUrl)
    return (
      url.protocol === 'http:' &&
      url.username === '' &&
      url.password === '' &&
      origins.has(url.origin)
    )
  } catch {
    return false
  }
}

export function isAllowedExternalUrl(
  rawUrl: string,
  allowedHosts: ReadonlySet<string>,
): boolean {
  try {
    const url = new URL(rawUrl)
    return (
      url.protocol === 'https:' &&
      url.username === '' &&
      url.password === '' &&
      allowedHosts.has(url.hostname)
    )
  } catch {
    return false
  }
}

export function assertTrustedSenderUrl(
  rawUrl: string,
  origins: ReadonlySet<string>,
): void {
  if (!isAllowedAppUrl(rawUrl, origins)) {
    throw new Error('Untrusted IPC sender')
  }
}

export function parseRoute(value: unknown): string {
  if (
    typeof value !== 'string' ||
    value.length === 0 ||
    value.length > 2048 ||
    !value.startsWith('/') ||
    value.startsWith('//') ||
    value.includes('://') ||
    value.includes('\\') ||
    /[\r\n\0]/u.test(value)
  ) {
    throw new TypeError('route must be a safe application-relative path')
  }
  return value
}

export function backendStatusSnapshot(state: BackendState): BackendStatusSnapshot {
  return { state }
}

export function parseBackendStatusSnapshot(value: unknown): BackendStatusSnapshot {
  const input = recordValue(value, 'backend status')
  assertKnownKeys(input, new Set(['state']), 'backend status')
  if (!['online', 'offline', 'restarting'].includes(String(input.state))) {
    throw new TypeError('backend status state is invalid')
  }
  return { state: input.state as BackendState }
}

export function parseWindowBounds(value: unknown): WindowBounds {
  const input = recordValue(value, 'bounds')
  assertKnownKeys(input, new Set(['x', 'y', 'width', 'height']), 'bounds')
  const bounds: WindowBounds = {
    x: finiteNumber(input.x, 'bounds.x'),
    y: finiteNumber(input.y, 'bounds.y'),
  }
  for (const key of ['width', 'height'] as const) {
    if (input[key] === undefined) continue
    const dimension = finiteNumber(input[key], `bounds.${key}`)
    if (dimension < 1 || dimension > 4096) {
      throw new RangeError(`bounds.${key} must be between 1 and 4096`)
    }
    bounds[key] = dimension
  }
  return bounds
}

export function parseMoveDelta(value: unknown): MoveDelta {
  const input = recordValue(value, 'delta')
  assertKnownKeys(input, new Set(['x', 'y']), 'delta')
  const delta = {
    x: finiteNumber(input.x, 'delta.x'),
    y: finiteNumber(input.y, 'delta.y'),
  }
  if (Math.abs(delta.x) > 2000 || Math.abs(delta.y) > 2000) {
    throw new RangeError('delta must be between -2000 and 2000')
  }
  return delta
}

export function parsePetSettingsPatch(
  value: unknown,
): Partial<PetSettings> {
  const input = recordValue(value, 'pet settings')
  assertKnownKeys(input, PET_SETTING_KEYS, 'pet setting')

  const patch: Partial<PetSettings> = {}
  for (const key of BOOLEAN_SETTING_KEYS) {
    const setting = input[key]
    if (setting === undefined) continue
    if (typeof setting !== 'boolean') {
      throw new TypeError(`${key} must be a boolean`)
    }
    patch[key] = setting
  }

  if (input.size !== undefined) {
    const size = finiteNumber(input.size, 'size')
    if (size < 128 || size > 260) {
      throw new RangeError('size must be between 128 and 260')
    }
    patch.size = size
  }

  if (input.position !== undefined) {
    if (input.position === null) {
      patch.position = null
    } else {
      const position = recordValue(input.position, 'position')
      assertKnownKeys(position, new Set(['x', 'y']), 'position')
      const x = finiteNumber(position.x, 'position.x')
      const y = finiteNumber(position.y, 'position.y')
      if (Math.abs(x) > 100000 || Math.abs(y) > 100000) {
        throw new RangeError('position is outside the supported desktop range')
      }
      patch.position = { x, y }
    }
  }

  if (input.petId !== undefined) {
    if (
      typeof input.petId !== 'string' ||
      !/^[A-Za-z0-9_-]{1,64}$/u.test(input.petId)
    ) {
      throw new TypeError('petId contains unsupported characters')
    }
    patch.petId = input.petId
  }

  return patch
}

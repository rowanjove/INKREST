import type { RouteLocationRaw } from 'vue-router'

import type { SnapshotAction } from '../../entities/project/projectSnapshot'

export function firstEnabledSnapshotAction(
  actions: readonly SnapshotAction[],
): SnapshotAction | null {
  return actions.find((action) => action.enabled) || null
}

export function resolveSnapshotActionLocation(
  action: SnapshotAction,
): RouteLocationRaw {
  if (action.kind === 'navigate' && action.target.startsWith('/')) {
    return action.target
  }
  return {
    path: '/production',
    query: { intent: action.target, confirm: '1' },
  }
}

export function resolveSnapshotActionHref(action: SnapshotAction): string {
  const location = resolveSnapshotActionLocation(action)
  if (typeof location === 'string') return location
  const path = typeof location.path === 'string' && location.path ? location.path : '/production'
  const params = new URLSearchParams()
  const query = location.query || {}
  for (const [key, value] of Object.entries(query)) {
    if (value == null) continue
    params.set(key, Array.isArray(value) ? String(value[0]) : String(value))
  }
  const search = params.toString()
  return search ? `${path}?${search}` : path
}

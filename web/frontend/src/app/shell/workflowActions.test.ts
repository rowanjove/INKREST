import { describe, expect, it } from 'vitest'

import type { SnapshotAction } from '../../entities/project/projectSnapshot'
import {
  firstEnabledSnapshotAction,
  resolveSnapshotActionHref,
  resolveSnapshotActionLocation,
} from './workflowActions'

describe('workflow actions', () => {
  it('chooses the first enabled recommendation', () => {
    const actions = [
      { id: 'blocked', enabled: false },
      { id: 'ready', enabled: true },
    ] as SnapshotAction[]

    expect(firstEnabledSnapshotAction(actions)?.id).toBe('ready')
  })

  it('keeps navigation actions direct', () => {
    expect(resolveSnapshotActionLocation({
      id: 'outline', label: '完善策划', kind: 'navigate', target: '/outline', enabled: true,
    })).toBe('/outline')
  })

  it('routes generation intents to a confirmation screen only', () => {
    expect(resolveSnapshotActionLocation({
      id: 'continue', label: '继续生产', kind: 'intent', target: 'novel_continue', enabled: true,
    })).toEqual({
      path: '/production',
      query: { intent: 'novel_continue', confirm: '1' },
    })
  })

  it('serializes generation intents to a confirmation href', () => {
    expect(resolveSnapshotActionHref({
      id: 'continue', label: '继续生产', kind: 'intent', target: 'novel_continue', enabled: true,
    })).toBe('/production?intent=novel_continue&confirm=1')
  })
})

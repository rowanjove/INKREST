import { describe, expect, it } from 'vitest'

import {
  TASK_STATUS_LABELS,
  isActiveTaskStatus,
  type TaskStatus,
} from './projectSnapshot'

describe('project snapshot task contract', () => {
  it('localizes all seven task states', () => {
    const statuses: TaskStatus[] = [
      'pending',
      'claimed',
      'running',
      'paused',
      'succeeded',
      'failed',
      'cancelled',
    ]

    expect(statuses.map((status) => TASK_STATUS_LABELS[status])).toEqual([
      '等待中',
      '已领取',
      '运行中',
      '已暂停',
      '已完成',
      '失败',
      '已取消',
    ])
  })

  it('treats only actionable states as active', () => {
    expect(isActiveTaskStatus('pending')).toBe(true)
    expect(isActiveTaskStatus('paused')).toBe(true)
    expect(isActiveTaskStatus('failed')).toBe(false)
    expect(isActiveTaskStatus('cancelled')).toBe(false)
  })
})

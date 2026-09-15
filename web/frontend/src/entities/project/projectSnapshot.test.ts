import { describe, expect, it } from 'vitest'

import {
  TASK_STATUS_LABELS,
  blockingIssueAction,
  blockingIssueDetail,
  isActiveTaskStatus,
  type BlockingIssue,
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

describe('project blocker recovery contract', () => {
  const issue = (overrides: Partial<BlockingIssue>): BlockingIssue => ({
    code: 'unknown',
    label: '阻塞',
    severity: 'error',
    source: 'readiness',
    ...overrides,
  })

  it('gives every blocker an actionable destination', () => {
    expect(blockingIssueAction(issue({ code: 'engine' }))).toEqual({
      label: '配置模型',
      target: '/config#models-providers',
    })
    expect(blockingIssueAction(issue({ code: 'outline_invalid' }))).toEqual({
      label: '先备份再修复',
      target: '/config#system-data',
    })
    expect(blockingIssueAction(issue({ code: 'assets' }))).toEqual({
      label: '管理资产',
      target: '/assets',
    })
    expect(blockingIssueAction(issue({ code: 'future_blocker' }))).toEqual({
      label: '检查项目数据',
      target: '/config#system-data',
    })
  })

  it('preserves chapter context and surfaces validation errors', () => {
    expect(blockingIssueAction(issue({ source: 'pipeline', chapter_id: '003' })).target)
      .toBe('/production?tab=reviews&chapter=003')
    expect(blockingIssueDetail(issue({
      errors: [{ message: 'runtime 字段格式错误' }, { msg: '缺少 provider' }],
    }))).toBe('runtime 字段格式错误；缺少 provider')
  })
})

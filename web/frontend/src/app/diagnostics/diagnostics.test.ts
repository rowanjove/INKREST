import { describe, expect, it } from 'vitest'

import type { ProjectSnapshot } from '../../entities/project/projectSnapshot'
import {
  buildDiagnosticsSummary,
  destinationForAction,
  qualityStatusLabel,
  taskTypeLabel,
} from './diagnostics'

const snapshot = (overrides: Partial<ProjectSnapshot> = {}): ProjectSnapshot => ({
  project: { id: 'demo', name: '演示项目' },
  workflow_mode: 'assisted',
  readiness: { ok: true, pending: [], warnings: [] },
  outline_progress: {
    exists: true,
    valid: true,
    title: '测试大纲',
    arc_count: 1,
    planned_chapters: 3,
    target_chapters: 10,
    error: null,
  },
  chapter_progress: { authoritative_completed: 2 },
  active_tasks: [],
  blocking_issues: [],
  quality_summary: { status: 'stable', total_reports: 2, passed: 2, failed: 0 },
  cost_summary: { persisted: { total_tokens: 1_250, total_cost_cny: 0.42 } },
  next_actions: [],
  updated_at: '2026-07-27T00:00:00Z',
  ...overrides,
})

describe('diagnostics summary', () => {
  it('prioritizes backend connectivity over project state', () => {
    expect(buildDiagnosticsSummary(snapshot(), 'offline', true)).toMatchObject({
      tone: 'danger',
      label: '服务离线',
    })
  })

  it('summarizes blockers, warnings and active tasks from one snapshot', () => {
    const value = snapshot({
      blocking_issues: [
        { code: 'outline_missing', label: '缺少大纲', severity: 'error', source: 'outline' },
      ],
      readiness: { ok: false, pending: [], warnings: ['备用模型未配置'] },
      active_tasks: [
        {
          id: 'task-1',
          project_id: 'demo',
          task_type: 'chapter',
          status: 'running',
          payload_json: {},
          result_json: null,
          attempt: 1,
          max_attempts: 3,
          claim_token: null,
          lease_expires_at: null,
          heartbeat_at: null,
          checkpoint: null,
          status_reason: null,
          created_at: '2026-07-27T00:00:00Z',
          started_at: null,
          finished_at: null,
        },
      ],
    })

    expect(buildDiagnosticsSummary(value, 'online', false)).toEqual({
      tone: 'danger',
      label: '1 项阻断',
      blockerCount: 1,
      warningCount: 1,
      activeTaskCount: 1,
    })
  })

  it('localizes internal quality and task enums', () => {
    expect(qualityStatusLabel('missing')).toBe('暂无报告')
    expect(qualityStatusLabel('low')).toBe('质量偏低')
    expect(qualityStatusLabel('stable')).toBe('质量稳定')
    expect(taskTypeLabel('chapter_batch')).toBe('批量章节')
  })

  it('keeps intent actions behind a confirmation-page navigation', () => {
    expect(destinationForAction({
      id: 'continue',
      label: '继续写作',
      kind: 'intent',
      target: 'continue-novel',
      enabled: true,
    })).toBe('/workspace?intent=continue-novel')
  })
})

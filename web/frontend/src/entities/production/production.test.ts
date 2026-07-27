import { describe, expect, it } from 'vitest'
import {
  createProductionActionIntent,
  filterProductionReviews,
  filterProductionTasks,
  resolveReviewActionTargets,
  type ProductionReviewItem,
  type ProductionTask,
} from './production'

const task = (overrides: Partial<ProductionTask>): ProductionTask => ({
  id: 't-1',
  project_id: 'book',
  task_type: 'chapter',
  task_type_label: '单章生产',
  status: 'running',
  status_label: '运行中',
  chapter_id: '003',
  goal: '推进剧情',
  attempt: 1,
  max_attempts: 2,
  step: 'writer',
  step_label: '正文写作',
  checkpoint: { resumable_from: null, progress: null },
  status_reason: null,
  failure_code: null,
  failure_message: null,
  recovery_action: 'cancel',
  heartbeat_at: null,
  lease_expires_at: null,
  created_at: '2026-07-27T00:00:00Z',
  started_at: null,
  finished_at: null,
  ...overrides,
})

const review = (overrides: Partial<ProductionReviewItem>): ProductionReviewItem => ({
  chapter_id: '003',
  chapter_title: '第三章',
  stage: 'quality_blocked',
  stage_label: '质量阻断',
  severity: 'error',
  message: '质量未通过',
  overall_score: 48,
  issues: [],
  completed_stages: [],
  updated_at: null,
  recommended_action: 'edit_then_gate',
  ...overrides,
})

describe('production center contracts', () => {
  it('filters tasks by durable status and searchable context', () => {
    const tasks = [
      task({ id: 'running', status: 'running' }),
      task({ id: 'failed', status: 'failed', failure_message: '模型超时' }),
      task({ id: 'done', status: 'succeeded' }),
    ]
    expect(filterProductionTasks(tasks, 'active', '')).toHaveLength(1)
    expect(filterProductionTasks(tasks, 'failed', '超时')[0]?.id).toBe('failed')
    expect(filterProductionTasks(tasks, 'finished', '')[0]?.id).toBe('done')
  })

  it('filters review items without exposing internal codes as the primary copy', () => {
    const items = [
      review({ chapter_id: '003' }),
      review({
        chapter_id: '004',
        chapter_title: '第四章',
        severity: 'warning',
        stage: 'external_review_pending',
        stage_label: '等待外审',
      }),
    ]
    expect(filterProductionReviews(items, 'external', '')[0]?.chapter_id).toBe('004')
    expect(filterProductionReviews(items, 'all', '第三章')).toHaveLength(1)
  })

  it('resolves only action-compatible review targets', () => {
    const items = [
      review({ chapter_id: '003', stage: 'quality_blocked' }),
      review({ chapter_id: '004', stage: 'external_review_pending' }),
      review({ chapter_id: '005', stage: 'batch_retry' }),
    ]
    expect(resolveReviewActionTargets('rerun_gate', items)).toEqual(['003'])
    expect(resolveReviewActionTargets('external_passed', items)).toEqual(['004'])
    expect(resolveReviewActionTargets('rewrite', items)).toEqual(['003', '005'])
  })

  it('creates an explicit confirmation intent without executing an action', () => {
    const intent = createProductionActionIntent('rewrite', {
      chapterIds: ['003', '003', '005'],
    })
    expect(intent.chapterIds).toEqual(['003', '005'])
    expect(intent.label).toBe('重新生产章节')
    expect(intent.description).toContain('修订历史')
    expect(intent.tone).toBe('danger')
  })
})

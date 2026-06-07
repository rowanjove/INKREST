import { describe, expect, it } from 'vitest'
import { hasPipelineProblem, mapContextToPetState } from './petState'

const baseContext = {
  backend_health: 'ok',
  running_tasks: [],
  failed_tasks: [],
  pipeline_active: false,
  pipeline_pending: { pending_total: 0 },
}

describe('mapContextToPetState', () => {
  it('shows working when pipeline runs despite stale failed tasks', () => {
    const state = mapContextToPetState(
      {
        ...baseContext,
        running_tasks: [{ id: 'task-running' }],
        failed_tasks: [{ id: 'task-failed' }],
        pipeline_active: true,
      },
      [],
    )
    expect(state).toBe('working')
  })

  it('stays idle when only repair queue backlog exists', () => {
    const state = mapContextToPetState(
      {
        ...baseContext,
        pipeline_pending: { pending_total: 3 },
      },
      [],
    )
    expect(state).toBe('idle')
  })

  it('shows question when idle with unignored failed tasks', () => {
    const state = mapContextToPetState(
      {
        ...baseContext,
        failed_tasks: [{ id: 'task-failed' }],
      },
      [],
    )
    expect(state).toBe('question')
  })

  it('shows question when batch is paused', () => {
    const state = mapContextToPetState(
      {
        ...baseContext,
        novel_batch: { paused: true },
        running_tasks: [{ id: 'task-running' }],
      },
      [],
    )
    expect(state).toBe('question')
  })
})

describe('hasPipelineProblem', () => {
  it('ignores repair backlog without failed tasks', () => {
    expect(
      hasPipelineProblem(
        { ...baseContext, pipeline_pending: { pending_total: 2 } },
        [],
      ),
    ).toBe(false)
  })
})
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api/projectSnapshot', () => ({
  getCurrentProjectSnapshot: vi.fn(),
}))

import { getCurrentProjectSnapshot } from '../api/projectSnapshot'
import type { ProjectSnapshot } from '../entities/project/projectSnapshot'
import { useProjectSnapshotStore } from './projectSnapshot'

const getSnapshotMock = vi.mocked(getCurrentProjectSnapshot)

function snapshot(projectId: string, completed = 0): ProjectSnapshot {
  return {
    project: { id: projectId, name: projectId },
    workflow_mode: 'assisted',
    readiness: { ok: true, pending: [], warnings: [] },
    outline_progress: {
      exists: true,
      valid: true,
      title: projectId,
      arc_count: 1,
      planned_chapters: 10,
      target_chapters: 10,
      error: null,
    },
    chapter_progress: { authoritative_completed: completed },
    active_tasks: [],
    blocking_issues: [],
    quality_summary: { status: 'missing', total_reports: 0, passed: 0, failed: 0 },
    cost_summary: { persisted: { total_tokens: 0, total_cost_cny: 0 } },
    next_actions: [],
    updated_at: '2026-07-27T00:00:00Z',
  }
}

describe('project snapshot store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getSnapshotMock.mockReset()
  })

  it('deduplicates concurrent refreshes for one project', async () => {
    let resolveRequest!: (value: ProjectSnapshot) => void
    getSnapshotMock.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )
    const store = useProjectSnapshotStore()

    const first = store.refresh('book-1')
    const second = store.refresh('book-1')
    resolveRequest(snapshot('book-1'))
    await Promise.all([first, second])

    expect(getSnapshotMock).toHaveBeenCalledTimes(1)
    expect(store.snapshot?.project.id).toBe('book-1')
    expect(store.status).toBe('ready')
  })

  it('ignores a stale response after the active project changes', async () => {
    let resolveOld!: (value: ProjectSnapshot) => void
    getSnapshotMock
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveOld = resolve
        }),
      )
      .mockResolvedValueOnce(snapshot('book-2', 2))
    const store = useProjectSnapshotStore()

    const oldRequest = store.refresh('book-1')
    store.invalidate('book-2')
    await store.refresh('book-2')
    resolveOld(snapshot('book-1', 1))
    await oldRequest

    expect(store.snapshot?.project.id).toBe('book-2')
    expect(store.snapshot?.chapter_progress.authoritative_completed).toBe(2)
  })

  it('retains the last valid snapshot when a refresh fails', async () => {
    getSnapshotMock
      .mockResolvedValueOnce(snapshot('book-1', 3))
      .mockRejectedValueOnce(new Error('offline'))
    const store = useProjectSnapshotStore()

    await store.refresh('book-1')
    await store.refresh('book-1', { force: true })

    expect(store.snapshot?.chapter_progress.authoritative_completed).toBe(3)
    expect(store.status).toBe('error')
    expect(store.error).toBe('offline')
  })
})

import { describe, expect, it, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api', () => ({
  listTasks: vi.fn(() => Promise.resolve({ data: [] })),
  abortTask: vi.fn(),
  getRuntimeLogs: vi.fn(() => Promise.resolve({ data: { logs: [], last_id: 0 } })),
  clearRuntimeLogs: vi.fn(),
}))

import { listTasks } from '../api'
import { useTasksStore } from './tasks'

const listTasksMock = vi.mocked(listTasks)

describe('tasks processTasksList', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listTasksMock.mockResolvedValue({ data: [] } as any)
  })

  it('does not rewind live progress with an older HTTP snapshot', async () => {
    const store = useTasksStore()
    store.addProgress({
      step: 'writer',
      status: 'done',
      chapter_id: '001',
      timestamp: 2_000_000_000_000,
      task_id: 'task-live',
    })
    listTasksMock.mockResolvedValueOnce({
      data: [
        {
          task_id: 'task-live',
          chapter_id: '001',
          status: 'running',
          pipeline_progress: [
            {
              step: 'planner',
              status: 'running',
              chapter_id: '001',
              timestamp: 1_000,
              task_id: 'task-live',
            },
          ],
        },
      ],
    } as any)

    await store.refreshTaskList()
    expect(store.progress.some((entry) => entry.step === 'writer' && entry.status === 'done')).toBe(
      true,
    )
  })

  it('keeps isRunning when local progress is running but API list is empty', async () => {
    const store = useTasksStore()
    store.addProgress({
      step: 'ensure_queue',
      status: 'running',
      chapter_id: '',
      timestamp: Date.now(),
    })
    expect(store.isRunning).toBe(true)

    await store.refreshTaskList()
    expect(store.isRunning).toBe(true)
    expect(store.progress.some((p) => p.step === 'ensure_queue' && p.status === 'running')).toBe(
      true,
    )
  })

  it('does not let a paused novel task hide a running chapter repair', async () => {
    const store = useTasksStore()
    listTasksMock.mockResolvedValueOnce({
      data: [
        {
          task_id: 'task-running-repair',
          chapter_id: '003',
          status: 'running',
          goal: 'rewrite chapter',
          progress: { step: 'writer', status: 'running', chapter_id: '003' },
        },
        {
          task_id: 'task-paused-novel',
          chapter_id: '001',
          status: 'paused',
          goal: 'Novel: continue',
        },
      ],
    } as any)

    await store.refreshTaskList()

    expect(store.isRunning).toBe(true)
    expect(store.currentTaskId).toBe('task-running-repair')
    expect(store.currentChapterId).toBe('003')
  })

  it('keeps the paused production task id when nothing is running', async () => {
    const store = useTasksStore()
    listTasksMock.mockResolvedValueOnce({
      data: [
        {
          task_id: 'task-paused-novel',
          chapter_id: '001',
          status: 'paused',
          goal: 'Novel: continue',
        },
      ],
    } as any)

    await store.refreshTaskList()

    expect(store.isRunning).toBe(false)
    expect(store.currentTaskId).toBe('task-paused-novel')
  })

  it('marks pending standard chapter tasks as recoverable running work', async () => {
    const store = useTasksStore()
    listTasksMock.mockResolvedValueOnce({
      data: [
        {
          task_id: 'task-resume-1',
          chapter_id: '001',
          status: 'pending',
          goal: 'draft chapter',
          status_reason: 'process_interrupted',
          resumable_from: 'writer',
        },
      ],
    } as any)

    await store.refreshTaskList()

    expect(store.isRunning).toBe(true)
    expect(store.currentTaskId).toBe('task-resume-1')
    expect(store.currentChapterId).toBe('001')
    expect(store.taskList[0].resumable_from).toBe('writer')
  })

  it('logs manuscript conflicts once when a succeeded task kept the human edit', async () => {
    const store = useTasksStore()
    listTasksMock.mockResolvedValue({
      data: [
        {
          task_id: 'task-conflict-1',
          chapter_id: '002',
          status: 'succeeded',
          result: {
            manuscript_sync: 'conflict',
            warnings: ['正文在生成期间被编辑，已保留人工稿，生成结果未覆盖'],
          },
        },
      ],
    } as any)

    await store.refreshTaskList()
    await store.refreshTaskList()

    const conflictLogs = store.logs.filter((entry) =>
      entry.message.includes('已保留人工稿'),
    )
    expect(conflictLogs).toHaveLength(1)
    expect(store.lastTaskWarning?.task_id).toBe('task-conflict-1')
  })

  it('hydrates persisted pipeline history for the latest completed task after restart', async () => {
    const store = useTasksStore()
    listTasksMock.mockResolvedValueOnce({
      data: [{
        task_id: 'novel-complete',
        chapter_id: '002',
        status: 'succeeded',
        goal: 'Novel: continue',
        pipeline_progress: [
          { step: 'writer', status: 'done', chapter_id: '001', timestamp: 1 },
          { step: 'writer', status: 'done', chapter_id: '002', timestamp: 2 },
          { step: 'unified_gate', status: 'done', chapter_id: '002', timestamp: 3 },
        ],
      }],
    } as any)

    await store.refreshTaskList()

    expect(store.currentTaskId).toBe('novel-complete')
    expect(store.currentChapterId).toBe('002')
    expect(store.isRunning).toBe(false)
    expect(store.progress).toHaveLength(3)
  })
})

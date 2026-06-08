import { describe, expect, it, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api', () => ({
  listTasks: vi.fn(() => Promise.resolve({ data: [] })),
  abortTask: vi.fn(),
  getRuntimeLogs: vi.fn(() => Promise.resolve({ data: { logs: [], last_id: 0 } })),
  clearRuntimeLogs: vi.fn(),
}))

import { useTasksStore } from './tasks'

describe('tasks processTasksList', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
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
})
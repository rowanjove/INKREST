import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api', () => ({
  listProjects: vi.fn(),
  getCurrentProject: vi.fn(),
  createProject: vi.fn(),
  deleteProject: vi.fn(),
  switchProject: vi.fn(),
}))

import { getCurrentProject, listProjects } from '../api'
import { useProjectStore } from './project'

const listProjectsMock = vi.mocked(listProjects)
const getCurrentProjectMock = vi.mocked(getCurrentProject)

describe('project store hydration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('deduplicates startup hydration and resolves the active project', async () => {
    listProjectsMock.mockResolvedValue({
      data: [{ id: 'book-1', name: '第一本书' }],
    } as never)
    getCurrentProjectMock.mockResolvedValue({
      data: { id: 'book-1', name: '第一本书' },
    } as never)
    const store = useProjectStore()

    await Promise.all([store.hydrate(), store.hydrate()])

    expect(listProjectsMock).toHaveBeenCalledTimes(1)
    expect(getCurrentProjectMock).toHaveBeenCalledTimes(1)
    expect(store.currentProject?.id).toBe('book-1')
    expect(store.hydrationStatus).toBe('ready')
  })

  it('exposes a retryable error state instead of pretending hydration succeeded', async () => {
    listProjectsMock.mockRejectedValue(new Error('offline'))
    getCurrentProjectMock.mockRejectedValue(new Error('offline'))
    const store = useProjectStore()

    await store.hydrate()

    expect(store.hydrationStatus).toBe('error')
    expect(store.hydrationError).toBe('offline')
    expect(store.currentProject).toBeNull()
  })
})

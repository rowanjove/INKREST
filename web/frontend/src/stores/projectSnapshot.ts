import { defineStore } from 'pinia'
import { ref } from 'vue'

import { getCurrentProjectSnapshot } from '../api/projectSnapshot'
import type { ProjectSnapshot } from '../entities/project/projectSnapshot'

export type SnapshotLoadStatus = 'idle' | 'loading' | 'ready' | 'error'

export const useProjectSnapshotStore = defineStore('project-snapshot', () => {
  const snapshot = ref<ProjectSnapshot | null>(null)
  const projectId = ref<string | null>(null)
  const status = ref<SnapshotLoadStatus>('idle')
  const error = ref('')
  const loadedAt = ref<number | null>(null)
  let request: Promise<void> | null = null
  let generation = 0

  function invalidate(nextProjectId: string | null = null) {
    generation += 1
    request = null
    projectId.value = nextProjectId
    snapshot.value = null
    status.value = 'idle'
    error.value = ''
    loadedAt.value = null
  }

  function refresh(
    requestedProjectId: string,
    options: { force?: boolean } = {},
  ): Promise<void> {
    if (!requestedProjectId) {
      invalidate(null)
      return Promise.resolve()
    }
    if (projectId.value !== requestedProjectId) {
      invalidate(requestedProjectId)
    }
    if (request && !options.force) return request

    const requestGeneration = generation
    status.value = 'loading'
    error.value = ''
    const pending = getCurrentProjectSnapshot()
      .then((value) => {
        if (
          requestGeneration !== generation ||
          value.project.id !== requestedProjectId
        ) {
          return
        }
        snapshot.value = value
        status.value = 'ready'
        loadedAt.value = Date.now()
      })
      .catch((reason: unknown) => {
        if (requestGeneration !== generation) return
        status.value = 'error'
        error.value = reason instanceof Error ? reason.message : '项目状态加载失败'
      })
      .finally(() => {
        if (request === pending) request = null
      })
    request = pending
    return pending
  }

  return {
    snapshot,
    projectId,
    status,
    error,
    loadedAt,
    invalidate,
    refresh,
  }
})

import type { ProjectSnapshot } from '../entities/project/projectSnapshot'
import api from './client'

export async function getCurrentProjectSnapshot(): Promise<ProjectSnapshot> {
  const { data } = await api.get<ProjectSnapshot>('/projects/current/snapshot')
  return data
}

export async function getProjectSnapshot(projectId: string): Promise<ProjectSnapshot> {
  const { data } = await api.get<ProjectSnapshot>(`/projects/${projectId}/snapshot`)
  return data
}

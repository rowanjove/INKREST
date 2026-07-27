import type { FactoryDashboard, FactoryMode } from '../types/factory'
import api from './client'

export const importDemoProject = (demoId = 'demo-factory-novel') =>
  api.post('/projects/import-demo', null, { params: { demo_id: demoId } })

export async function getFactoryDashboard(): Promise<FactoryDashboard> {
  const { data } = await api.get<FactoryDashboard>('/factory/dashboard')
  return data
}

export async function updateFactoryMode(mode: FactoryMode): Promise<{ status: string; mode: FactoryMode }> {
  const { data } = await api.put<{ status: string; mode: FactoryMode }>('/factory/mode', { mode })
  return data
}

export async function getFactoryStudio() {
  const { data } = await api.get('/factory/studio')
  return data
}

export const batchExportProjects = (projectIds: string[]) =>
  api.post('/projects/batch-export-zip', { project_ids: projectIds }, { responseType: 'blob' })

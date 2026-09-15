import { request as requestFactory } from '@playwright/test'

type ProjectSummary = { id?: string; name?: string; description?: string }
type TaskSummary = { project_id?: string; task_id?: string; status?: string }

/** Remove only the deterministic E2E fixture projects after the web server stops serving tests. */
export default async function globalTeardown() {
  const context = await requestFactory.newContext({
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:8000',
  })
  try {
    const setup = await context.get('/api/auth/local-setup', {
      headers: { 'X-Novel-Agent-Local-Client': '1' },
    })
    const token = setup.ok() ? String((await setup.json()).token || '') : ''
    const headers = token ? { 'X-Novel-Agent-Token': token } : {}
    const projectsResponse = await context.get('/api/projects', { headers })
    if (!projectsResponse.ok()) return
    const projects = (await projectsResponse.json()) as ProjectSummary[]
    for (const project of projects) {
      if (project.name !== 'E2E维护场景' || project.description !== 'Playwright E2E fixture' || !project.id) {
        continue
      }
      const tasksResponse = await context.get('/api/chapters/tasks', { headers })
      if (tasksResponse.ok()) {
        const tasks = (await tasksResponse.json()) as TaskSummary[]
        for (const task of tasks) {
          if (
            task.project_id === project.id &&
            task.task_id &&
            ['pending', 'queued', 'claimed', 'running'].includes(String(task.status))
          ) {
            await context.post(`/api/chapters/tasks/${encodeURIComponent(task.task_id)}/abort`, { headers })
          }
        }
      }
      await context.delete(`/api/projects/${encodeURIComponent(project.id)}`, { headers })
    }
  } finally {
    await context.dispose()
  }
}

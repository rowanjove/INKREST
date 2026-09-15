import { APIRequestContext, Page, expect, test } from '@playwright/test'

export type MaintenanceSeed = {
  project_id: string
  project_name: string
  batch_paused: boolean
  pause_reason: string
  last_chapter_id: string
  pending_chapter_ids: string[]
  pending_total: number
}

const fixtureProjectIds = new Set<string>()

async function fetchAccessToken(request: APIRequestContext): Promise<string> {
  const setupRes = await request.get('/api/auth/local-setup', {
    headers: { 'X-Novel-Agent-Local-Client': '1' },
  })
  if (!setupRes.ok()) return ''
  const body = (await setupRes.json()) as { token?: string }
  return body.token ?? ''
}

function authHeaders(token: string): Record<string, string> {
  return token ? { 'X-Novel-Agent-Token': token } : {}
}

export async function injectLocalAccessToken(
  page: Page,
  request: APIRequestContext,
): Promise<void> {
  const token = await fetchAccessToken(request)
  await page.addInitScript((stored: string) => {
    if (stored) window.localStorage.setItem('novel-agent-access-token', stored)
  }, token)
}

export async function seedMaintenanceScenario(
  request: APIRequestContext,
): Promise<MaintenanceSeed> {
  const token = await fetchAccessToken(request)
  const res = await request.post('/api/e2e/seed-maintenance-scenario', {
    headers: authHeaders(token),
  })
  expect(res.ok()).toBeTruthy()
  const seed = (await res.json()) as MaintenanceSeed
  if (seed.project_id) fixtureProjectIds.add(seed.project_id)
  return seed
}

async function cleanupFixtureProjects(request: APIRequestContext): Promise<void> {
  const projectIds = [...fixtureProjectIds]
  if (!projectIds.length) return

  const token = await fetchAccessToken(request)
  const headers = authHeaders(token)
  for (const projectId of projectIds) {
    const tasksResponse = await request.get('/api/chapters/tasks', { headers })
    if (tasksResponse.ok()) {
      const tasks = (await tasksResponse.json()) as Array<{ project_id?: string; task_id?: string; status?: string }>
      for (const task of tasks) {
        if (
          task.project_id === projectId &&
          task.task_id &&
          ['pending', 'queued', 'claimed', 'running'].includes(String(task.status))
        ) {
          await request.post(`/api/chapters/tasks/${encodeURIComponent(task.task_id)}/abort`, { headers })
        }
      }
    }
    const deleteResponse = await request.delete(`/api/projects/${encodeURIComponent(projectId)}`, { headers })
    if (deleteResponse.ok()) fixtureProjectIds.delete(projectId)
    else expect(deleteResponse.ok()).toBeTruthy()
  }
}

test.afterEach(async ({ request }) => cleanupFixtureProjects(request))
test.afterAll(async ({ request }) => cleanupFixtureProjects(request))

function projectNav(page: Page) {
  return page.getByRole('navigation', { name: '项目导航' })
}

/** Load the seeded project through the V2 hydration guard. */
export async function ensureActiveProject(
  page: Page,
  request: APIRequestContext,
): Promise<MaintenanceSeed> {
  await injectLocalAccessToken(page, request)
  const seed = await seedMaintenanceScenario(request)
  await page.goto('/workspace')
  const nav = projectNav(page)
  await expect(nav).toBeVisible({ timeout: 15_000 })
  await expect(page.getByRole('heading', { name: seed.project_name })).toBeVisible({
    timeout: 15_000,
  })
  return seed
}

async function navigateInApp(page: Page, path: string): Promise<void> {
  await page.goto(path)
  await page.waitForLoadState('domcontentloaded')
}

/** Seed a fixture project and verify that direct deep links hydrate correctly. */
export async function openWithActiveProject(
  page: Page,
  request: APIRequestContext,
  path: string,
): Promise<MaintenanceSeed> {
  const seed = await ensureActiveProject(page, request)
  if (path !== '/workspace') {
    await navigateInApp(page, path)
  }
  return seed
}

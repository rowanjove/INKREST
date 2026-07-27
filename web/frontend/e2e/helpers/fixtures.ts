import { APIRequestContext, Page, expect } from '@playwright/test'

export type MaintenanceSeed = {
  project_id: string
  project_name: string
  batch_paused: boolean
  pause_reason: string
  last_chapter_id: string
  pending_chapter_ids: string[]
  pending_total: number
}

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
  return (await res.json()) as MaintenanceSeed
}

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

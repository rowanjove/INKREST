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
  const setupRes = await request.get('/api/auth/local-setup')
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

function mainNav(page: Page) {
  return page.getByRole('navigation', { name: '主导航' })
}

/** Load seeded project into the SPA (avoid full reload on guarded routes — Pinia resets). */
export async function ensureActiveProject(
  page: Page,
  request: APIRequestContext,
): Promise<MaintenanceSeed> {
  await injectLocalAccessToken(page, request)
  const seed = await seedMaintenanceScenario(request)
  await page.goto('/')
  const nav = mainNav(page)
  await expect(nav).toBeVisible({ timeout: 15_000 })
  await nav.getByRole('button', { name: '工作台' }).click()
  await expect(page.getByRole('heading', { name: '工作台' })).toBeVisible({ timeout: 15_000 })
  return seed
}

async function navigateInApp(page: Page, path: string): Promise<void> {
  const [pathname, queryPart] = path.split('?')
  const params = new URLSearchParams(queryPart ?? '')
  const nav = mainNav(page)

  if (pathname.startsWith('/monitor')) {
    await nav.getByRole('button', { name: '日志中心' }).click()
    await expect(page.getByRole('heading', { name: '日志中心' })).toBeVisible({ timeout: 15_000 })
    const tab = params.get('tab')
    if (tab && tab !== 'task_logs') {
      if (tab === 'logs') {
        await page.getByRole('tab', { name: /费用与接口/ }).click()
      } else if (tab === 'agent_logs') {
        await page.getByRole('tab', { name: /Agent 实时日志/ }).click()
      }
    }
    return
  }

  if (pathname === '/chapters/list' || pathname.startsWith('/chapters/list')) {
    await nav.getByRole('button', { name: '章节' }).click()
    await page.getByRole('link', { name: /章节列表/ }).click()
    await expect(page.locator('.chapters-page')).toBeVisible({ timeout: 15_000 })
    return
  }

  if (pathname.startsWith('/chapters/maintenance')) {
    await nav.getByRole('button', { name: '章节' }).click()
    await page.getByRole('link', { name: /章节维护/ }).click()
    await expect(page.getByRole('heading', { name: '修章队列' })).toBeVisible({ timeout: 15_000 })
    if (params.get('expand') === 'alerts') {
      const body = page.locator('#pipeline-alerts-section .pipeline-panel__body')
      if (!(await body.isVisible())) {
        await page.locator('#pipeline-alerts-section .pipeline-panel__head--toggle').click()
      }
    }
    return
  }

  if (pathname === '/workspace') {
    await nav.getByRole('button', { name: '工作台' }).click()
    await expect(page.getByRole('heading', { name: '工作台' })).toBeVisible({ timeout: 15_000 })
    return
  }

  if (pathname === '/writer') {
    await nav.getByRole('button', { name: '写作' }).click()
    await expect(page.locator('.chapter-sidebar .sidebar-title')).toContainText('章节目录', {
      timeout: 15_000,
    })
    return
  }

  if (pathname === '/state') {
    await nav.getByRole('button', { name: '状态库' }).click()
    await expect(page.getByRole('heading', { name: '状态库' })).toBeVisible({ timeout: 15_000 })
    return
  }

  if (pathname === '/outline') {
    await nav.getByRole('button', { name: '大纲' }).click()
    await expect(page.getByRole('heading', { name: '作品大纲' })).toBeVisible({ timeout: 15_000 })
    return
  }

  if (pathname === '/assets') {
    await nav.getByRole('button', { name: '项目资产' }).click()
    await expect(page.getByRole('heading', { name: '资产编辑' })).toBeVisible({ timeout: 15_000 })
    return
  }

  if (pathname === '/pet-bubble') {
    await page.goto('/pet-bubble')
    await expect(page.locator('.bubble-header-bar')).toBeVisible({ timeout: 15_000 })
    return
  }

  if (pathname === '/') {
    await page.getByRole('button', { name: /栖墨/ }).click()
    await expect(page.getByRole('heading', { name: '我的书库' })).toBeVisible({ timeout: 15_000 })
  }
}

/** Seed fixture project and navigate without full page reload on guarded routes. */
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
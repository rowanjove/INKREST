import { test, expect } from '@playwright/test'
import { injectLocalAccessToken, openWithActiveProject } from './helpers/fixtures'

test.describe('route smoke coverage', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('config page renders settings nav', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/config')
    await expect(page.getByRole('heading', { name: '设置' })).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.config-nav .nav-chip').first()).toBeVisible()
  })

  test('monitor log center renders split task pane', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/monitor?tab=task_logs')
    await expect(page.getByRole('heading', { name: '日志中心' })).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.task-rounds-split')).toBeVisible()
  })

  test('trope workshop renders blueprint panel', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/trope-workshop')
    await expect(page.getByRole('heading', { name: '网文套路设计工坊' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.locator('.blueprint-slots, .trope-workshop-layout').first()).toBeVisible()
  })

  test('library home renders empty or grid', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '我的书库' })).toBeVisible({ timeout: 15_000 })
    await expect(
      page.locator('.empty-library, .project-grid').first(),
    ).toBeVisible()
  })
})
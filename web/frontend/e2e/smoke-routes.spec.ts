import { test, expect } from '@playwright/test'
import { injectLocalAccessToken, openWithActiveProject } from './helpers/fixtures'

test.describe('route smoke coverage', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('config page renders settings nav', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/config')
    await expect(page.getByRole('heading', { level: 1, name: '设置' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.locator('.config-nav .nav-chip').first()).toBeVisible()
  })

  test('production center renders the unified task workspace', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/production?tab=runs')
    await expect(page.getByRole('heading', { name: '生产中心' })).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.task-workspace')).toBeVisible()
  })

  test('planning canvas nodes remain visible and selectable', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/outline')
    const outlineNode = page.locator('.vue-flow__node[data-id="A01"]')
    await expect(outlineNode).toBeVisible({ timeout: 15_000 })
    await outlineNode.click()
    await expect(page.locator('.inspector h2')).toHaveText('未命名')
  })

  test('legacy trope route redirects into the unified create flow', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/trope-workshop')
    await expect(page.getByRole('heading', { name: '新建作品' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page).toHaveURL(/\/create\?source=template/)
    await expect(page.getByText('确认建档', { exact: true })).toBeVisible()
  })

  test('legacy onboarding route redirects into the four-step create flow', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/onboarding')
    await expect(page.getByRole('heading', { name: '新建作品' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page).toHaveURL(/\/create(?:\?welcome=1)?$/)
    await expect(page.getByText('工作方式', { exact: true })).toBeVisible()
    await expect(page.getByText('素材来源', { exact: true })).toBeVisible()
    await expect(page.getByText('写作规格', { exact: true })).toBeVisible()
    await expect(page.getByText('确认建档', { exact: true })).toBeVisible()
  })

  test('library home renders empty or grid', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '我的书库' })).toBeVisible({ timeout: 15_000 })
    await expect(
      page.locator('.empty-library, .project-grid').first(),
    ).toBeVisible()
  })

  test('production logs tab renders project and LLM log shells', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/production?tab=logs')
    await expect(page.getByRole('heading', { name: '生产中心' })).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Agent 实时日志')).toBeVisible()
    await expect(page.locator('.llm-log-card').first()).toBeVisible({ timeout: 15_000 })
  })
})

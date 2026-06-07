import { test, expect } from '@playwright/test'
import { injectLocalAccessToken, openWithActiveProject } from './helpers/fixtures'

test.describe('chapter list and plugin manager', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('chapter list shows table and gate rerun action', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/chapters/list')
    await expect(page.locator('.chapters-page')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('button', { name: '只重跑门禁' }).first()).toBeVisible()
  })

  test('plugin manager loads plugin grid', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/plugins')
    await expect(page.getByRole('heading', { name: /插件生态管理/ })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.locator('.plugins-grid-container')).toBeVisible()
    await expect(
      page.locator('.plugins-grid, .el-empty').first(),
    ).toBeVisible()
  })
})
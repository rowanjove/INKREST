import { test, expect } from '@playwright/test'
import { ensureActiveProject } from './helpers/fixtures'

test.describe('batch run safety', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('library loads and the project deep link restores the snapshot overview', async ({ page, request }) => {
    const seed = await ensureActiveProject(page, request)
    await page.getByRole('button', { name: '返回书库' }).click()
    await expect(page.getByRole('heading', { name: '我的书库' })).toBeVisible({
      timeout: 15_000,
    })
    await page.goto('/workspace')
    await expect(page.getByRole('heading', { name: seed.project_name })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByRole('heading', { name: '安全的下一步' })).toBeVisible()
  })

  test('blocked projects expose repair intent without a direct generation control', async ({ page, request }) => {
    await ensureActiveProject(page, request)
    await expect(page.getByRole('heading', { name: '当前阻塞' })).toBeVisible()
    await expect(page.getByRole('button', { name: /处理阻断项/ })).toBeVisible()
    await expect(page.getByRole('button', { name: '连写启动' })).toHaveCount(0)
    await expect(page.getByRole('dialog', { name: /连写启动|继续写书/ })).toHaveCount(0)
  })
})

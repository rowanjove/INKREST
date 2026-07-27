import { test, expect } from '@playwright/test'
import { ensureActiveProject } from './helpers/fixtures'

test.describe('batch run safety', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('library loads and the project deep link restores the batch entry', async ({ page, request }) => {
    await ensureActiveProject(page, request)
    await page.getByRole('button', { name: '返回书库' }).click()
    await expect(page.getByRole('heading', { name: '我的书库' })).toBeVisible({
      timeout: 15_000,
    })
    await page.goto('/workspace')
    await expect(page.getByRole('button', { name: '连写启动' })).toBeVisible({
      timeout: 15_000,
    })
  })

  test('batch start remains blocked while the opening checklist is incomplete', async ({ page, request }) => {
    await ensureActiveProject(page, request)
    const batchBtn = page.getByRole('button', { name: '连写启动' })
    await expect(batchBtn).toBeVisible({ timeout: 15_000 })
    await expect(batchBtn).toBeDisabled()
    await expect(page.getByText('开书清单红灯，请先补齐')).toBeVisible()
    await expect(page.getByRole('dialog', { name: /连写启动|继续写书/ })).toHaveCount(0)
  })
})

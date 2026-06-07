import { test, expect } from '@playwright/test'

test.describe('batch run dialog', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('library loads and workbench shows batch start entry', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: '新建小说' })).toBeVisible({
      timeout: 15_000,
    })
    await page.goto('/workspace')
    await expect(page.getByRole('button', { name: /连写启动|继续写书/ })).toBeVisible({
      timeout: 15_000,
    })
  })
})
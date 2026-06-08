import { test, expect } from '@playwright/test'
import { ensureActiveProject } from './helpers/fixtures'

test.describe('batch run dialog', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('library loads and workbench shows batch start entry', async ({ page, request }) => {
    await ensureActiveProject(page, request)
    await page.getByRole('button', { name: /栖墨/ }).click()
    await expect(page.getByRole('heading', { name: '我的书库' })).toBeVisible({
      timeout: 15_000,
    })
    await page.getByRole('navigation', { name: '主导航' }).getByRole('button', { name: '工作台' }).click()
    await expect(page.getByRole('button', { name: '连写启动' })).toBeVisible({
      timeout: 15_000,
    })
  })

  test('batch start opens dialog and keeps it visible', async ({ page, request }) => {
    await ensureActiveProject(page, request)
    const batchBtn = page.getByRole('button', { name: '连写启动' })
    await expect(batchBtn).toBeVisible({ timeout: 15_000 })
    await batchBtn.click()
    const dialog = page.getByRole('dialog', { name: /连写启动|继续写书/ })
    await expect(dialog).toBeVisible({ timeout: 15_000 })
    await page.waitForTimeout(800)
    await expect(dialog).toBeVisible()
    // 种子场景含熔断暂停 → 主按钮为「仍继续写书」；无暂停时为「确认连写」
    await expect(
      dialog.getByRole('button', { name: /确认连写|仍继续写书/ }),
    ).toBeVisible()
  })
})
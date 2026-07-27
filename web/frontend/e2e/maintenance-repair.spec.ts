import { test, expect } from '@playwright/test'
import { openWithActiveProject } from './helpers/fixtures'

test.describe('production review workspace', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('review tab shows normalized repair queue', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/production?tab=reviews')
    await expect(page.getByText('审校与修复', { exact: true })).toBeVisible({
      timeout: 15_000,
    })
    await page.getByText('第三章 门后的影子').click()
    await expect(page.getByText('文风与表达')).toBeVisible()
  })

  test('seeded queue supports filters and chapter selection', async ({ page, request }) => {
    const seed = await openWithActiveProject(page, request, '/production?tab=reviews')
    expect(seed.pending_total).toBeGreaterThan(0)

    await expect(page.locator('.el-segmented__item-label').getByText('阻断', { exact: true })).toBeVisible()
    await expect(page.locator('.el-segmented__item-label').getByText('外审', { exact: true })).toBeVisible()
    await expect(page.getByText('第二章 失踪的钟声').first()).toBeVisible()
    await expect(page.getByText('第三章 门后的影子').first()).toBeVisible()
  })

  test('repair action opens confirmation without executing it', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/production?tab=reviews')
    await page.getByText('第三章 门后的影子').click()
    await page.getByRole('button', { name: '重跑门禁', exact: true }).click()
    await expect(page.locator('.el-dialog')).toBeVisible()
    await expect(page.getByText('确认生产动作')).toBeVisible()
    await expect(page.getByText('只有点击下方确认按钮后才会提交')).toBeVisible()
    await page.getByRole('button', { name: '取消', exact: true }).click()
    await expect(page.locator('.el-dialog')).not.toBeVisible()
    await expect(page.getByRole('heading', { name: '第三章 门后的影子' })).toBeVisible()
  })
})

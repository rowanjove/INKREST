import { test, expect } from '@playwright/test'
import { openWithActiveProject } from './helpers/fixtures'

test.describe('chapter maintenance', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('maintenance page shows repair queue section', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/chapters/maintenance')
    await expect(page.getByRole('heading', { name: '修章队列' })).toBeVisible({
      timeout: 15_000,
    })
  })

  test('seeded queue shows pending chapters and filter tabs', async ({ page, request }) => {
    const seed = await openWithActiveProject(page, request, '/chapters/maintenance?expand=alerts')
    expect(seed.pending_total).toBeGreaterThan(0)

    await expect(page.getByRole('heading', { name: '修章队列' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.locator('#pipeline-alerts-section .pipeline-panel__body')).toBeVisible()
    await expect(page.getByText('内部门禁（栖墨统一门禁）')).toBeVisible()
    await expect(page.getByRole('radio', { name: '门禁阻断' })).toBeVisible()
    await expect(page.getByRole('radio', { name: '批量跳过' })).toBeVisible()
    await expect(page.getByText('第 002 章').first()).toBeVisible()
    await expect(page.getByText('第 003 章').first()).toBeVisible()
  })

  test('seeded pause shows repair-first banner on maintenance', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/chapters/maintenance')
    await expect(page.locator('.batch-status-banner').getByText('全书批量已暂停（门禁阻断）')).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByRole('button', { name: '先处理待处理章' })).toBeVisible()
    await expect(page.getByRole('button', { name: '仍继续写书' })).toBeVisible()
  })
})
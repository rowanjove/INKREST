import { test, expect } from '@playwright/test'
import { openWithActiveProject } from './helpers/fixtures'

test.describe('production center operations', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('runs tab keeps queue, durable timeline, and task logs together', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/production?tab=runs')
    await expect(page.getByRole('heading', { name: '生产中心' })).toBeVisible({ timeout: 15_000 })
    const failedTask = page.locator('.task-row').filter({ hasText: '第 003 章' })
    await expect(failedTask).toBeVisible()
    await failedTask.click()
    await expect(page.getByText('任务 e2e-production-failed')).toBeVisible()
    await expect(page.getByRole('heading', { name: '状态时间线' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '任务日志' })).toBeVisible()
    await expect(page.getByText('文风与表达未达到质量门禁要求').first()).toBeVisible()
  })

  test('production center shows repair-first pause banner', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/production?tab=runs')
    await expect(page.locator('.pause-banner').getByText('自动生产已暂停：质量门禁阻断')).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByRole('button', { name: '处理待修章节' })).toBeVisible()
    await expect(page.getByRole('button', { name: '仍要继续' })).toBeVisible()
  })

  test('production center fits desktop viewports in light and dark themes', async ({ page, request }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await openWithActiveProject(page, request, '/production?tab=reviews')
    await expect(page.locator('.production-canvas')).toBeVisible()
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    ).toBe(true)

    await page.evaluate(() => localStorage.setItem('inkrest-theme-mode', 'dark'))
    await page.reload()
    await expect(page.locator('html.dark')).toHaveAttribute('data-theme', 'dark')
    await page.setViewportSize({ width: 1100, height: 720 })
    await expect(page.getByRole('heading', { name: '生产中心' })).toBeVisible()
    await expect(page.locator('.review-workspace')).toBeVisible()
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    ).toBe(true)
    await page.evaluate(() => localStorage.setItem('inkrest-theme-mode', 'light'))
  })
})

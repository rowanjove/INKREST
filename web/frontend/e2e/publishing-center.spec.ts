import { expect, test } from '@playwright/test'

import { openWithActiveProject } from './helpers/fixtures'

test.describe('publishing center', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('previews canonical chapters and keeps chapter selection in the URL', async ({
    page,
    request,
  }) => {
    await openWithActiveProject(page, request, '/publishing?tab=preview&chapter=001')
    await expect(page.getByRole('heading', { name: '发布中心' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.locator('.book-sheet')).toContainText('CHAPTER 001')
    const second = page.locator('.catalog-list button').nth(1)
    await second.click()
    await expect(page).toHaveURL(/\/publishing\?.*chapter=002/)
    await expect(page.locator('.book-sheet')).toContainText('CHAPTER 002')
    await expect(page.locator('.book-sheet')).toContainText('文稿修订 R1')
  })

  test('keeps platform rules, golden chapters, and feedback in one workspace', async ({
    page,
    request,
  }) => {
    await openWithActiveProject(page, request, '/publishing?tab=platform&chapter=001')
    await expect(page.getByRole('heading', { name: '目标平台' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByRole('heading', { name: '黄金三章' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '外站读者反馈' })).toBeVisible()
    await expect(page.getByText('页面打开时仅执行确定性检查，不调用模型。')).toBeVisible()
  })

  test('shows blocking preflight and preserves the legacy reader URL', async ({
    page,
    request,
  }) => {
    await openWithActiveProject(page, request, '/reader')
    await expect(page).toHaveURL(/\/publishing/)
    await page.getByRole('button', { name: /导出交付/ }).click()
    await expect(page.getByRole('heading', { name: '发布前检查' })).toBeVisible()
    await expect(page.getByText('审校仍有阻断项')).toBeVisible()
    await expect(page.getByRole('button', { name: '检查并下载' })).toBeDisabled()
  })

  test('fits light and dark desktop viewports without page overflow', async ({
    page,
    request,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await openWithActiveProject(page, request, '/publishing?tab=preview')
    await expect(page.locator('.publishing-canvas')).toBeVisible()
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    ).toBe(true)

    await page.evaluate(() => localStorage.setItem('inkrest-theme-mode', 'dark'))
    await page.reload()
    await page.setViewportSize({ width: 1100, height: 720 })
    await expect(page.locator('html.dark')).toHaveAttribute('data-theme', 'dark')
    await expect(page.locator('.book-sheet')).toBeVisible()
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    ).toBe(true)
    await page.evaluate(() => localStorage.setItem('inkrest-theme-mode', 'light'))
  })
})

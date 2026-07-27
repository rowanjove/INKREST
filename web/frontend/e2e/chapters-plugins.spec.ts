import { test, expect } from '@playwright/test'
import { injectLocalAccessToken, openWithActiveProject } from './helpers/fixtures'

test.describe('manuscript center and plugin manager', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('legacy chapter list route opens the unified manuscript center', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/chapters/list')
    await expect(page).toHaveURL(/\/writer/)
    await expect(page.locator('.manuscript-page')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByLabel('正文编辑器')).toBeVisible()
    await expect(page.getByRole('complementary', { name: '章节目录' })).toBeVisible()
  })

  test('editor auto-saves and reading mode reuses the current document', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/writer?chapter=001')
    const editor = page.getByLabel('正文编辑器')
    await expect(editor).toContainText('林越推开门')

    await editor.click()
    await page.keyboard.press('Control+End')
    await page.keyboard.type('窗外传来三声短促的敲击。')
    await expect(page.getByText('已自动保存', { exact: true })).toBeVisible({
      timeout: 10_000,
    })

    await page.reload()
    await expect(page.getByLabel('正文编辑器')).toContainText('窗外传来三声短促的敲击。')
    await page.getByText('阅读', { exact: true }).click()
    await expect(page.getByRole('navigation', { name: '正文格式' })).toHaveCount(0)
    await expect(page.getByLabel('正文编辑器')).toContainText('窗外传来三声短促的敲击。')

    await page.getByRole('button', { name: '历史' }).click()
    await page.getByRole('button', { name: /修订 1/ }).click()
    const revisionDialog = page.getByRole('dialog', { name: '历史修订预览' })
    await expect(revisionDialog).toContainText('雨落在旧城的青石路上。')
    await revisionDialog.getByRole('button', { name: '恢复为新的当前修订' }).click()
    await expect(page.getByText('已自动保存', { exact: true })).toBeVisible()
    await expect(page.getByLabel('正文编辑器')).not.toContainText('窗外传来三声短促的敲击。')
  })

  test('plugin manager loads plugin grid', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/plugins')
    await expect(page.getByRole('heading', { name: '扩展中心' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.locator('.plugins-grid-container')).toBeVisible()
    await expect(
      page.locator('.plugins-grid, .el-empty').first(),
    ).toBeVisible()
  })
})

import { test, expect } from '@playwright/test'
import { openWithActiveProject } from './helpers/fixtures'

test.describe('writer and state views', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('writer page shows virtual chapter tree and Tiptap toolbar', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/writer')
    await expect(page.getByRole('complementary', { name: '章节目录' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByRole('navigation', { name: '正文格式' })).toBeVisible()
    await expect(page.getByLabel('正文编辑器')).toBeVisible()
    await expect(page.getByText('已自动保存', { exact: true })).toBeVisible()
  })

  test('state page shows outer tabs and settings sub-tabs', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/state')
    await expect(page.getByRole('heading', { name: '状态库' })).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('tab', { name: /剧情设定库/ })).toBeVisible()
    await expect(page.getByRole('tab', { name: /时空编年史/ })).toBeVisible()
    await expect(page.getByRole('tab', { name: '人物图鉴' })).toBeVisible()
  })

  test('state chronicle tab switches to relation graph', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/state')
    await page.getByRole('tab', { name: /时空编年史/ }).click()
    await expect(page.getByRole('tab', { name: '人物图谱' })).toBeVisible({ timeout: 10_000 })
    await page.getByRole('tab', { name: '人物图谱' }).click()
    await expect(page.locator('#relations-svg, .relations-hint').first()).toBeVisible()
  })
})

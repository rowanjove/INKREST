import { test, expect } from '@playwright/test'
import {
  ensureActiveProject,
  injectLocalAccessToken,
  openWithActiveProject,
} from './helpers/fixtures'

test.describe('V2 application shell', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 to execute')

  test('shows exactly four global destinations without an active project', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.route('**/api/projects/current', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    })
    await page.goto('/create')

    const primary = page.getByRole('navigation', { name: '全局导航' })
    const utility = page.getByRole('navigation', { name: '全局入口' })
    await expect(primary.getByRole('button')).toHaveText(['书库', '新建作品'])
    await expect(utility.getByRole('button')).toHaveText(['设置', '扩展'])
  })

  test('hydrates deep links and keeps five project centers', async ({ page, request }) => {
    await ensureActiveProject(page, request)
    const navigation = page.getByRole('navigation', { name: '项目导航' })
    await expect(navigation.getByRole('button')).toHaveText([
      '概览',
      '策划',
      '正文',
      '生产',
      '发布',
    ])

    await page.goto('/writer')
    await expect(navigation.getByRole('button', { name: '正文' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(page.locator('.chapter-sidebar .sidebar-title')).toContainText('章节目录', {
      timeout: 15_000,
    })
  })

  test('opens keyboard command search without executing generation', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/workspace')
    await page.keyboard.press('Control+K')
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await dialog.getByRole('textbox', { name: '搜索页面、章节、人物或命令' }).fill('设置')
    await expect(dialog.getByRole('option', { name: /设置/ }).first()).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
  })

  test('opens diagnostics and fits the minimum desktop viewport', async ({ page, request }) => {
    await page.setViewportSize({ width: 1100, height: 720 })
    await openWithActiveProject(page, request, '/workspace')
    await page.getByRole('button', { name: /运行状态/ }).click()
    await expect(page.getByRole('heading', { name: '运行诊断' })).toBeVisible()
    await expect(page.getByText('质量与成本')).toBeVisible()

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    )
    expect(overflow).toBeLessThanOrEqual(0)
  })
})

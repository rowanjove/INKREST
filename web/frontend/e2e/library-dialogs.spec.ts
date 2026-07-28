import { expect, test } from '@playwright/test'
import { openWithActiveProject } from './helpers/fixtures'

test.describe('library service dialogs', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('delete confirmation is centered and closing it is not an error', async ({
    page,
    request,
  }) => {
    const seed = await openWithActiveProject(page, request, '/')
    const menu = page.getByRole('button', {
      name: `${seed.project_name} 的操作菜单`,
    })

    await menu.click()
    await page.getByRole('menuitem', { name: '删除作品' }).click()

    const dialog = page.getByRole('dialog', { name: '删除小说' })
    const box = page.locator('.el-message-box')
    await expect(dialog).toBeVisible()
    await expect(box).toBeVisible()

    const bounds = await box.boundingBox()
    const viewport = page.viewportSize()
    expect(bounds).not.toBeNull()
    expect(viewport).not.toBeNull()
    expect(
      Math.abs(bounds!.x + bounds!.width / 2 - viewport!.width / 2),
    ).toBeLessThanOrEqual(1)
    // Element Plus applies a small optical upward offset. Keep enough tolerance
    // for that intentional positioning while still catching the unstyled
    // top-left dialog regression.
    expect(
      Math.abs(bounds!.y + bounds!.height / 2 - viewport!.height / 2),
    ).toBeLessThanOrEqual(40)

    await dialog.getByRole('button', { name: '关闭此对话框' }).click()

    await expect(dialog).toBeHidden()
    await expect(page.locator('.el-message').filter({ hasText: '删除失败' })).toHaveCount(0)
    await expect(page.getByRole('heading', { name: seed.project_name })).toBeVisible()
  })
})

import { test, expect } from '@playwright/test'
import { injectLocalAccessToken, openWithActiveProject } from './helpers/fixtures'

test.describe('assets and pet bubble views', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('assets page shows sidebar and editor panel', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/assets')
    await expect(page.getByRole('heading', { name: '资产编辑' })).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.asset-list')).toBeVisible()
    await expect(page.locator('.editor-panel')).toBeVisible()
  })

  test('pet bubble shows status tab and repair shortcut', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/pet-bubble')
    await expect(page.locator('.bubble-header-bar')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('button', { name: '状态' })).toBeVisible()
    await expect(page.getByRole('button', { name: '对话' })).toBeVisible()
    await expect(page.locator('.quick-actions-compact')).toContainText('修章')
  })

  test('pet bubble chat tab shows suggested questions', async ({ page, request }) => {
    await injectLocalAccessToken(page, request)
    await page.goto('/pet-bubble')
    await page.getByRole('button', { name: '对话' }).click()
    await expect(page.locator('.chat-suggestions-strip .suggest-chip').first()).toBeVisible({
      timeout: 10_000,
    })
  })
})
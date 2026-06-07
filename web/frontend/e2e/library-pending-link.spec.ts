import { test, expect } from '@playwright/test'

test.describe('library pending deep link', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('expand=alerts opens maintenance repair queue', async ({ page }) => {
    await page.goto('/chapters/maintenance?expand=alerts')
    await expect(page.getByRole('heading', { name: '修章队列' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.locator('#pipeline-alerts-section .pipeline-panel__body')).toBeVisible()
  })
})
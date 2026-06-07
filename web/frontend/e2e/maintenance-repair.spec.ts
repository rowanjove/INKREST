import { test, expect } from '@playwright/test'

test.describe('chapter maintenance', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('maintenance page shows repair queue section', async ({ page }) => {
    await page.goto('/chapters/maintenance')
    await expect(page.getByRole('heading', { name: '修章队列' })).toBeVisible({
      timeout: 15_000,
    })
  })
})
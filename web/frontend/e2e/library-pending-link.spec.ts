import { test, expect } from '@playwright/test'
import { openWithActiveProject } from './helpers/fixtures'

test.describe('library pending deep link', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('legacy maintenance link opens production review queue', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/chapters/maintenance?expand=alerts')
    await expect(page.getByRole('heading', { name: '生产中心' })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page).toHaveURL(/\/production\?.*tab=reviews/)
    await expect(page.getByText('审校与修复', { exact: true })).toBeVisible()
  })
})

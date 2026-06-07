import { test, expect } from '@playwright/test'
import { openWithActiveProject } from './helpers/fixtures'

test.describe('log center layout', () => {
  test.skip(!process.env.E2E_RUN, 'Set E2E_RUN=1 with backend running to execute')

  test('task logs tab uses left-right split for rounds and timeline', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/monitor?tab=task_logs')
    await expect(page.locator('.task-rounds-split')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('heading', { name: '连写轮次' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '任务流水日志' })).toBeVisible()
  })

  test('monitor shows batch pause banner when batch is paused', async ({ page, request }) => {
    await openWithActiveProject(page, request, '/monitor?tab=task_logs')
    await expect(page.locator('.batch-status-banner').getByText('全书批量已暂停（门禁阻断）')).toBeVisible({
      timeout: 15_000,
    })
  })
})
import { test } from '@playwright/test'
import path from 'path'
import { injectLocalAccessToken, openWithActiveProject } from './helpers/fixtures'

const outputDir = path.resolve(__dirname, '../../../docs/images')

test.describe('capture screenshots for readme', () => {
  test.use({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5,
  })

  test('capture all main views', async ({ page, request }) => {
    // 1. Library (Global)
    await injectLocalAccessToken(page, request)
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({
      path: path.join(outputDir, 'readme-library.png'),
      fullPage: false,
    })

    // 2. Overview / Workspace Dashboard (Project)
    await openWithActiveProject(page, request, '/workspace')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({
      path: path.join(outputDir, 'readme-overview.png'),
      fullPage: false,
    })

    // 3. Writer / Manuscript Workspace
    await page.goto('/writer')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({
      path: path.join(outputDir, 'readme-writer.png'),
      fullPage: false,
    })

    // 4. Inspiration Workshop / Blueprint
    await page.goto('/inspiration')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({
      path: path.join(outputDir, 'readme-blueprint.png'),
      fullPage: false,
    })

    // 5. Production Center
    await page.goto('/production?tab=runs')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({
      path: path.join(outputDir, 'readme-production.png'),
      fullPage: false,
    })

    // 6. Quality Center
    await page.goto('/quality')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({
      path: path.join(outputDir, 'readme-quality.png'),
      fullPage: false,
    })

    // 7. Publishing Center
    await page.goto('/publishing')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({
      path: path.join(outputDir, 'readme-publishing.png'),
      fullPage: false,
    })

    // 8. Plugin Platform 2.0
    await page.goto('/plugins')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({
      path: path.join(outputDir, 'readme-plugins.png'),
      fullPage: false,
    })
  })
})

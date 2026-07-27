import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'

import { chromium } from '@playwright/test'

const cdpPort = Number.parseInt(process.env.ELECTRON_CDP_PORT || '', 10)
if (!Number.isInteger(cdpPort) || cdpPort < 1 || cdpPort > 65535) {
  throw new Error('ELECTRON_CDP_PORT must be a valid local debugging port')
}

const outputDir = resolve(process.env.ELECTRON_SMOKE_OUTPUT || 'test-results/packaged-electron')
await mkdir(outputDir, { recursive: true })

const browser = await chromium.connectOverCDP(`http://127.0.0.1:${cdpPort}`)
let seededProjectId = ''
let mainPage = null
try {
  const context = browser.contexts()[0]
  if (!context) throw new Error('Packaged Electron browser context was not found')

  let pages = context.pages()
  for (let attempt = 0; attempt < 50 && pages.length < 2; attempt += 1) {
    await new Promise((resolveWait) => setTimeout(resolveWait, 100))
    pages = context.pages()
  }

  const page =
    pages.find((candidate) => !new URL(candidate.url()).pathname.startsWith('/pet')) ||
    pages[0]
  if (!page) throw new Error('Packaged Electron main renderer was not found')
  mainPage = page

  await page.waitForLoadState('domcontentloaded')
  await page.waitForFunction(() => Boolean(localStorage.getItem('novel-agent-access-token')))
  const seed = await page.evaluate(async () => {
    const token = localStorage.getItem('novel-agent-access-token') || ''
    const response = await fetch('/api/e2e/seed-maintenance-scenario', {
      method: 'POST',
      headers: { 'X-Novel-Agent-Token': token },
    })
    if (!response.ok) throw new Error(`Fixture seed failed: ${response.status}`)
    return response.json()
  })
  seededProjectId = String(seed.project_id || '')
  await page.evaluate(async () => {
    const token = localStorage.getItem('novel-agent-access-token') || ''
    const response = await fetch('/api/chapters/003', {
      method: 'DELETE',
      headers: { 'X-Novel-Agent-Token': token },
    })
    if (!response.ok) throw new Error(`Fixture cleanup failed: ${response.status}`)
  })

  const base = new URL(page.url()).origin
  await page.goto(`${base}/publishing?tab=preview&chapter=001`)
  await page.getByRole('heading', { name: '发布中心' }).waitFor({ state: 'visible' })
  await page.locator('.book-sheet').waitFor({ state: 'visible' })
  await page.locator('.publishing-page .el-loading-mask').waitFor({ state: 'hidden' })
  const noHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )
  if (!noHorizontalOverflow) throw new Error('Packaged publishing page has horizontal overflow')

  const screenshotPath = resolve(outputDir, 'packaged-publishing.png')
  await page.screenshot({ path: screenshotPath, fullPage: false })

  await page.getByRole('button', { name: /导出交付/ }).click()
  await page.getByRole('heading', { name: '生成成书文件' }).waitFor({ state: 'visible' })
  const formats = await page.locator('.format-grid button:not(:disabled)').count()
  if (formats !== 5) throw new Error(`Expected 5 packaged export formats, found ${formats}`)

  await page.getByRole('button', { name: '检查并下载' }).click()
  const confirmation = page.getByRole('dialog', { name: '确认导出' })
  await confirmation.waitFor({ state: 'visible' })
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/publishing/export') &&
      response.request().method() === 'POST',
  )
  await confirmation.getByRole('button', { name: '确认下载' }).click()
  const response = await responsePromise
  if (response.status() !== 200) {
    throw new Error(`Packaged UI export failed: ${response.status()}`)
  }
  const exported = await response.body()
  if (!exported.toString('utf8').includes('林越')) {
    throw new Error('Packaged UI export did not use the canonical SQLite manuscript')
  }

  process.stdout.write(
    `${JSON.stringify(
      {
        project_id: seed.project_id,
        renderer_url: page.url(),
        formats,
        export_status: response.status(),
        export_bytes: exported.length,
        no_horizontal_overflow: noHorizontalOverflow,
        screenshot: screenshotPath,
      },
      null,
      2,
    )}\n`,
  )
} finally {
  if (mainPage && seededProjectId && !mainPage.isClosed()) {
    await mainPage
      .evaluate(async (projectId) => {
        const token = localStorage.getItem('novel-agent-access-token') || ''
        const headers = { 'X-Novel-Agent-Token': token }
        const tasksResponse = await fetch('/api/chapters/tasks', { headers })
        if (tasksResponse.ok) {
          const tasks = await tasksResponse.json()
          for (const task of Array.isArray(tasks) ? tasks : []) {
            if (
              task.project_id === projectId &&
              ['pending', 'queued', 'running'].includes(task.status)
            ) {
              await fetch(
                `/api/chapters/tasks/${encodeURIComponent(task.task_id)}/abort`,
                { method: 'POST', headers },
              )
            }
          }
        }
        const deleteResponse = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
          method: 'DELETE',
          headers,
        })
        if (!deleteResponse.ok) {
          throw new Error(`Project cleanup failed: ${deleteResponse.status}`)
        }
      }, seededProjectId)
  }
  await browser.close()
}

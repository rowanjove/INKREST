import { defineConfig } from '@playwright/test'

const e2ePython =
  process.env.E2E_PYTHON || (process.platform === 'win32' ? 'py -3.12' : 'python3')

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:8000',
    headless: true,
  },
  webServer: process.env.E2E_SKIP_SERVER
    ? undefined
    : {
        command: `${e2ePython} ../../main.py serve --no-browser`,
        url: 'http://127.0.0.1:8000',
        reuseExistingServer: process.env.E2E_REUSE_SERVER === '1',
        timeout: 120_000,
        env: {
          ...process.env,
          E2E_FIXTURES: process.env.E2E_FIXTURES || '1',
        },
      },
})

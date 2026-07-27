import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const electronRoot = join(process.cwd(), 'electron')
const read = (relative: string) =>
  readFileSync(join(electronRoot, relative), 'utf-8')

describe('Electron main-process security contract', () => {
  it('enables the global sandbox before creating any window', () => {
    const main = read('main.ts')
    expect(main).toContain('app.enableSandbox()')
    expect(main.indexOf('app.enableSandbox()')).toBeLessThan(
      main.indexOf('new BrowserWindow'),
    )
    for (const file of [
      'main.ts',
      'windows/pet-window.ts',
      'windows/bubble-window.ts',
    ]) {
      const source = read(file)
      expect(source).toContain('contextIsolation: true')
      expect(source).toContain('nodeIntegration: false')
      expect(source).toContain('sandbox: true')
    }
  })

  it('starts the backend only for the single-instance lock owner', () => {
    const main = read('main.ts')
    expect(main).toContain('app.requestSingleInstanceLock()')
    expect(main).toContain('if (gotSingleInstanceLock) {')
    expect(main).toContain('app.whenReady().then')
    expect(main.indexOf('if (gotSingleInstanceLock) {')).toBeLessThan(
      main.indexOf('app.whenReady().then'),
    )
  })

  it('denies permission checks and waits for the exact backend child on exit', () => {
    const windowSecurity = read('window-security.ts')
    const main = read('main.ts')
    expect(windowSecurity).toContain('setPermissionCheckHandler(() => false)')
    expect(windowSecurity).toContain('setPermissionRequestHandler')
    expect(main).toContain('await bridge?.stopServer()')
    expect(main).not.toContain('setTimeout(resolve, 1500)')
  })
})

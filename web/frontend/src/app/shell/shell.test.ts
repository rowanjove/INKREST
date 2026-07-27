import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const src = join(dirname(fileURLToPath(import.meta.url)), '../..')
const read = (relative: string) => readFileSync(join(src, relative), 'utf-8')

describe('V2 application shell', () => {
  it('keeps App.vue as a small bootstrap and overlay assembler', () => {
    const source = read('App.vue')

    expect(source).toContain('AppShell')
    expect(source).not.toContain('getConfig')
    expect(source).not.toContain('listModels')
    expect(source.split(/\r?\n/).length).toBeLessThan(300)
  })

  it('renders one main landmark and delegates shell regions', () => {
    const source = read('app/shell/AppShell.vue')

    expect(source).toContain('AppSidebar')
    expect(source).toContain('AppTopbar')
    expect(source.match(/<main\b/g)).toHaveLength(1)
    expect(source).toContain('<router-view')
  })

  it('uses the canonical global and project navigation manifests', () => {
    const source = read('app/shell/AppSidebar.vue')

    expect(source).toContain('GLOBAL_NAV_ITEMS')
    expect(source).toContain('PROJECT_NAV_ITEMS')
    expect(source).not.toContain('灵感工坊')
    expect(source).not.toContain('日志中心')
  })
})

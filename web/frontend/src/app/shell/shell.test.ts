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
    expect(source).not.toContain('FirstBookGuide')
    expect(source.split(/\r?\n/).length).toBeLessThan(300)
  })

  it('renders one main landmark and delegates shell regions', () => {
    const source = read('app/shell/AppShell.vue')

    expect(source).toContain('AppSidebar')
    expect(source).toContain('AppTopbar')
    expect(source.match(/<main\b/g)).toHaveLength(1)
    expect(source).toContain('<router-view')
    expect(source).toContain("delete query.chapter")
  })

  it('uses the canonical global and project navigation manifests', () => {
    const source = read('app/shell/AppSidebar.vue')

    expect(source).toContain('GLOBAL_NAV_ITEMS')
    expect(source).toContain('PROJECT_NAV_ITEMS')
    expect(source).toContain('color: var(--color-text-sidebar)')
    expect(source).not.toContain('灵感工坊')
    expect(source).not.toContain('日志中心')
  })

  it('keeps quality directly visible in primary navigation without hiding behind details', () => {
    const navigation = read('app/router/navigation.ts')
    const sidebar = read('app/shell/AppSidebar.vue')

    expect(navigation).toContain("'quality'")
    expect(sidebar).not.toContain('<details')
    expect(sidebar).toContain("'project-journey'")
  })

  it('surfaces snapshot next actions without executing generation', () => {
    const topbar = read('app/shell/AppTopbar.vue')

    expect(topbar).toContain('首选下一步')
    expect(topbar).toContain('resolveSnapshotActionLocation')
    expect(topbar).not.toContain('continueNovel')
    expect(topbar).not.toContain('submitChapter')
  })

  it('equips sidebar with project switcher dialog and confirms exit on brand click', () => {
    const sidebar = read('app/shell/AppSidebar.vue')
    const topbar = read('app/shell/AppTopbar.vue')

    expect(sidebar).toContain('ProjectSwitcherDialog')
    expect(sidebar).toContain('showProjectSwitcher')
    expect(sidebar).toContain('handleBrandClick')
    expect(sidebar).toContain("route.meta.scope === 'project'")
    expect(topbar).toContain("route.meta.scope === 'project'")
  })
})

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const source = (name: string) =>
  readFileSync(fileURLToPath(new URL(`./${name}.vue`, import.meta.url)), 'utf8')

describe('shared UI primitives', () => {
  it('provide semantic status and error announcements', () => {
    expect(source('EmptyState')).toContain('role="status"')
    expect(source('ErrorState')).toContain('role="alert"')
    expect(source('ErrorState')).toContain("defineEmits<{ retry: [] }>()")
  })

  it('provide a consistent page heading and action slot', () => {
    const page = source('PageShell')
    expect(page).toContain('<h1>{{ title }}</h1>')
    expect(page).toContain('<slot name="actions" />')
  })

  it('stay presentational and make no business requests', () => {
    for (const name of ['PageShell', 'EmptyState', 'ErrorState', 'StatusBadge']) {
      const component = source(name)
      expect(component).not.toMatch(/from ['"].*(api|stores)/)
      expect(component).not.toContain('fetch(')
    }
  })
})

import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const srcRoot = join(dirname(fileURLToPath(import.meta.url)), '..')

describe('Element Plus service styles', () => {
  it('loads the teleported message and message-box styles from the app entry', () => {
    const main = readFileSync(join(srcRoot, 'main.ts'), 'utf-8')

    expect(main).toContain("element-plus/es/components/message/style/css")
    expect(main).toContain("element-plus/es/components/message-box/style/css")
    expect(main).toContain("element-plus/es/components/notification/style/css")
  })
})

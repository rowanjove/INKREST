import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

function read(rel: string): string {
  return readFileSync(join(root, rel), 'utf-8')
}

describe('refactored view subcomponents', () => {
  it('WritingWorkspace shell wires four writing child components', () => {
    const source = read('views/WritingWorkspace.vue')
    expect(source).toContain('WritingChapterSidebar')
    expect(source).toContain('WritingEditorMain')
    expect(source).toContain('WritingRightSidebar')
    expect(source).toContain('WritingWorkspaceDialogs')
  })

  it('WritingEditorMain keeps toolbar grid contract', () => {
    const source = read('components/writing/WritingEditorMain.vue')
    expect(source).toContain('grid-template-columns: repeat(auto-fit, minmax(84px, 1fr));')
    expect(source).toContain('btn-save')
    expect(source).toContain('btn-ai')
  })

  it('WritingChapterSidebar exposes chapter list actions', () => {
    const source = read('components/writing/WritingChapterSidebar.vue')
    expect(source).toContain('章节目录')
    expect(source).toContain('onDeleteChapter')
    expect(source).toContain('defineModel<boolean>(\'collapsed\'')
  })

  it('StateView shell wires settings and chronicle tabs', () => {
    const source = read('views/StateView.vue')
    expect(source).toContain('StateSettingsTab')
    expect(source).toContain('StateChronicleTab')
    expect(source).toContain('剧情设定库')
    expect(source).toContain('时空编年史')
  })

  it('StateChronicleTab keeps relation graph markers', () => {
    const source = read('components/state/StateChronicleTab.vue')
    expect(source).toContain('NODE_CIRCLE_R')
    expect(source).toContain('RELATION_TYPE_COLORS')
    expect(source).toContain('relations-svg')
  })

  it('StateSettingsTab keeps foreshadow collect action', () => {
    const source = read('components/state/StateSettingsTab.vue')
    expect(source).toContain('伏笔债务')
    expect(source).toContain('onCollect')
    expect(source).toContain('强行催收')
  })

  it('LibraryView shell uses book grid and dialogs', () => {
    const source = read('views/LibraryView.vue')
    expect(source).toContain('LibraryBookGrid')
    expect(source).toContain('LibraryDialogs')
    expect(source).toContain('EmptyStatePanel')
  })

  it('LibraryBookGrid keeps spine and pending badge markup', () => {
    const source = read('components/library/LibraryBookGrid.vue')
    expect(source).toContain('book-spine-shadow')
    expect(source).toContain('book-spine')
    expect(source).toContain('pending-badge')
    expect(source).toContain('aria-hidden="true"')
  })

  it('OutlineView shell keeps progress help above queue status', () => {
    const source = read('views/OutlineView.vue')
    const templateStart = source.search(/<template[\s>]/)
    expect(templateStart).toBeGreaterThan(-1)
    const template = source.slice(templateStart)
    const helpIdx = template.indexOf('<NovelProgressHelp')
    const queueIdx = template.indexOf('<OutlineQueueStatus')
    expect(helpIdx).toBeGreaterThan(-1)
    expect(queueIdx).toBeGreaterThan(helpIdx)
  })

  it('OutlineView delegates viewport to mindmap and classic panes', () => {
    const source = read('views/OutlineView.vue')
    expect(source).toContain('OutlineMindmapPane')
    expect(source).toContain('OutlineClassicPane')
    expect(source).toContain('OutlineDialogs')
  })
})
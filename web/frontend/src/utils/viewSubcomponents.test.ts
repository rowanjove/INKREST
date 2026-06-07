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

  it('AssetEditor shell wires sidebar, panel, and dialogs', () => {
    const source = read('views/AssetEditor.vue')
    expect(source).toContain('AssetListSidebar')
    expect(source).toContain('AssetEditorPanel')
    expect(source).toContain('AssetEditorDialogs')
    expect(source).toContain('useAssetEditor')
  })

  it('AssetEditorPanel keeps source toggle contract', () => {
    const source = read('components/asset/AssetEditorPanel.vue')
    expect(source).toContain('showAssetSource')
    expect(source).toContain('@click="showAssetSource = !showAssetSource"')
    expect(source).toContain(':show-source="showAssetSource"')
  })

  it('AssetListSidebar keeps custom asset bulk actions', () => {
    const source = read('components/asset/AssetListSidebar.vue')
    expect(source).toContain('导入名词解释')
    expect(source).toContain('onBulkImportToTerminology')
    expect(source).toContain('onContextCommand')
  })

  it('PetBubbleView shell wires status and chat tabs', () => {
    const source = read('views/PetBubbleView.vue')
    expect(source).toContain('PetBubbleStatusTab')
    expect(source).toContain('PetBubbleChatTab')
    expect(source).toContain('usePetBubbleView')
    expect(source).toContain('bubble-header-bar')
  })

  it('PetBubbleStatusTab keeps abort and maintenance navigation', () => {
    const source = read('components/pet/PetBubbleStatusTab.vue')
    expect(source).toContain('status-detail-desc')
    expect(source.replace(/\s/g, '')).toContain('>中止<')
    expect(source).toContain('🔧 修章')
  })

  it('PetBubbleChatTab keeps welcome card modifier', () => {
    const source = read('components/pet/PetBubbleChatTab.vue')
    expect(source).toContain('welcome: index === 0 && msg.role')
    expect(source).toContain('msg-bubble.welcome')
  })

  it('ChapterList shell wires table, repair dialog, and composable', () => {
    const source = read('views/ChapterList.vue')
    expect(source).toContain('ChapterListTable')
    expect(source).toContain('ChapterRepairDialog')
    expect(source).toContain('useChapterList')
  })

  it('ChapterListTable keeps gate rerun and edit action contract', () => {
    const source = read('components/chapter/ChapterListTable.vue')
    expect(source).toContain('只重跑门禁')
    expect(source).toContain('onRerunGateOnly')
    expect(source).toContain('class="chapter-edit-btn"')
    expect(source.replace(/\s/g, '')).toContain('>编辑<')
    expect(source).toContain('v-if="!row.is_missing"')
  })

  it('ChapterRepairDialog keeps goal suggest and submit actions', () => {
    const source = read('components/chapter/ChapterRepairDialog.vue')
    expect(source).toContain('AI 读入大纲')
    expect(source).toContain('运行章节流水线')
    expect(source).toContain('onSuggestGoal')
    expect(source).toContain('onSubmitRepair')
  })

  it('PluginManager shell wires metrics, filter, grid, and dialogs', () => {
    const source = read('views/PluginManager.vue')
    expect(source).toContain('PluginMetricsCards')
    expect(source).toContain('PluginFilterBar')
    expect(source).toContain('PluginGrid')
    expect(source).toContain('PluginManagerDialogs')
    expect(source).toContain('usePluginManager')
    expect(source).toContain('PluginAuthorHelpDialog')
  })

  it('PluginGrid keeps status indicator and card actions', () => {
    const source = read('components/plugin/PluginGrid.vue')
    expect(source).toContain('status-indicator')
    expect(source).toContain('pulse-dot')
    expect(source).toContain('onShowDetail')
    expect(source).toContain('onToggle')
  })

  it('PluginManagerDialogs keeps install dropzone and config schema form', () => {
    const source = read('components/plugin/PluginManagerDialogs.vue')
    expect(source).toContain('install-dropzone')
    expect(source).toContain('inkrest.plugin.json')
    expect(source).toContain('config_schema.properties')
  })

  it('TropeWorkshop shell wires component library and blueprint panel', () => {
    const source = read('views/TropeWorkshop.vue')
    expect(source).toContain('TropeComponentLibrary')
    expect(source).toContain('TropeBlueprintPanel')
    expect(source).toContain('useTropeWorkshop')
    expect(source).toContain('网文套路设计工坊')
  })

  it('TropeComponentLibrary keeps draggable component cards', () => {
    const source = read('components/trope/TropeComponentLibrary.vue')
    expect(source).toContain("defineModel<TropeTab>('activeTab'")
    expect(source).toContain('draggable="true"')
    expect(source).toContain('card-add-btn')
    expect(source).toContain('onAddToBlueprint')
  })

  it('TropeBlueprintPanel keeps blueprint slots and guide preview', () => {
    const source = read('components/trope/TropeBlueprintPanel.vue')
    expect(source).toContain('blueprint-slots')
    expect(source).toContain('markdown-preview')
    expect(source).toContain('以此新建作品')
    expect(source).toContain('应用到当前作品')
  })

  it('ReaderView shell wires toolbar, catalog, and content pane', () => {
    const source = read('views/ReaderView.vue')
    expect(source).toContain('ReaderToolbar')
    expect(source).toContain('ReaderCatalogDrawer')
    expect(source).toContain('ReaderContentPane')
    expect(source).toContain('useReaderView')
  })

  it('ReaderContentPane keeps bottom chapter navigation cards', () => {
    const source = read('components/reader/ReaderContentPane.vue')
    expect(source).toContain('bottom-navigator')
    expect(source).toContain('去写作页改稿')
    expect(source).toContain('novel-content-sheet')
  })

  it('ChapterDetail shell wires alerts, header, tabs, and edit dialog', () => {
    const source = read('views/ChapterDetail.vue')
    expect(source).toContain('ChapterDetailAlerts')
    expect(source).toContain('ChapterDetailHeader')
    expect(source).toContain('ChapterDetailTabs')
    expect(source).toContain('ChapterDetailEditDialog')
    expect(source).toContain('useChapterDetail')
  })

  it('ChapterDetailHeader hides rewrite actions without final text', () => {
    const source = read('components/chapter/ChapterDetailHeader.vue')
    expect(source).toContain('v-if="hasFinalText"')
    expect(source).toContain('整章重写')
    expect(source).toContain('编辑本章')
  })

  it('CreateWizard shell wires mode tabs and three creation panes', () => {
    const source = read('views/CreateWizard.vue')
    expect(source).toContain('CreateModeTabs')
    expect(source).toContain('CreateQuickPane')
    expect(source).toContain('CreateParsePane')
    expect(source).toContain('CreateAiPane')
    expect(source).toContain('useCreateWizard')
  })

  it('CreateModeTabs keeps default quick-create recommendation tag', () => {
    const source = read('components/create/CreateModeTabs.vue')
    expect(source).toContain('快速创建')
    expect(source).toContain('内容分析导入')
    expect(source).toContain('AI 创作引导')
    expect(source).toContain('rec-tag')
  })

  it('ConfigView shell wires navigation and sections stack', () => {
    const source = read('views/ConfigView.vue')
    expect(source).toContain('ConfigPageNav')
    expect(source).toContain('ConfigSectionsStack')
    expect(source).toContain('useConfigNavigation')
    expect(source).toContain('.config-page :deep(.fold-head)')
  })

  it('MonitorView shell wires tabs pane composable', () => {
    const source = read('views/MonitorView.vue')
    expect(source).toContain('MonitorTabsPane')
    expect(source).toContain('useMonitorView')
    expect(source).toContain('min-height: calc(100vh - 96px)')
  })

  it('MonitorTabsPane keeps task rounds split layout', () => {
    const source = read('components/monitor/MonitorTabsPane.vue')
    expect(source).toContain('task-rounds-split')
    expect(source).toContain('CostSummaryPanel')
    expect(source).toContain('hide-recent-rounds')
  })

  it('PetView shell uses window interaction composable', () => {
    const source = read('views/PetView.vue')
    expect(source).toContain('usePetWindowInteraction')
    expect(source).toContain('pet-hit-area')
  })

  it('ChaptersLayout delegates subnav to ChapterSubnav', () => {
    const source = read('views/ChaptersLayout.vue')
    expect(source).toContain('ChapterSubnav')
    const subnav = read('components/chapter/ChapterSubnav.vue')
    expect(subnav).toContain('to="/chapters/list"')
    expect(subnav).toContain('chapter-subnav__badge')
  })
})
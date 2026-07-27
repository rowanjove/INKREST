import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

function read(rel: string): string {
  return readFileSync(join(root, rel), 'utf-8')
}

describe('refactored view subcomponents', () => {
  it('WritingWorkspace shell wires the unified manuscript center', () => {
    const source = read('views/WritingWorkspace.vue')
    expect(source).toContain('ManuscriptChapterTree')
    expect(source).toContain('ManuscriptEditor')
    expect(source).toContain('ManuscriptInspector')
    expect(source).toContain('useManuscriptWorkspace')
    expect(source).toContain('Splitpanes')
  })

  it('ManuscriptEditor persists Tiptap JSON without a textarea', () => {
    const source = read('components/manuscript/ManuscriptEditor.vue')
    expect(source).toContain('@tiptap/vue-3')
    expect(source).toContain('instance.getJSON()')
    expect(source).not.toContain('<textarea')
  })

  it('ManuscriptChapterTree virtualizes and filters the chapter list', () => {
    const source = read('components/manuscript/ManuscriptChapterTree.vue')
    expect(source).toContain('章节目录')
    expect(source).toContain('useVirtualizer')
    expect(source).toContain('搜索章节')
    expect(source).toContain("emit('select'")
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
    expect(source).toContain("shared/ui/EmptyState.vue")
    expect(source).toContain('PageShell')
  })

  it('LibraryBookGrid keeps comparable metadata and one unified menu', () => {
    const source = read('components/library/LibraryBookGrid.vue')
    expect(source).toContain('project-cover')
    expect(source).toContain('project-meta')
    expect(source).toContain('el-dropdown-menu')
    expect(source).toContain('重命名')
    expect(source).toContain('未解决风险')
    expect(source).toContain('aria-hidden="true"')
    expect(source).toMatch(/class="menu-button"(?:(?!\/>)[\s\S])*@click\.stop/)
  })

  it('OutlineView provides one three-pane planning workspace', () => {
    const source = read('views/OutlineView.vue')
    expect(source).toContain('Splitpanes')
    expect(source).toContain('PlanningEntityTree')
    expect(source).toContain('PlanningCanvas')
    expect(source).toContain('PlanningInspector')
  })

  it('keeps the existing outline editor available inside planning', () => {
    const shell = read('views/OutlineView.vue')
    const source = read('views/OutlineEditorLegacy.vue')
    expect(shell).toContain('OutlineEditorLegacy')
    expect(source).toContain('OutlineMindmapPane')
    expect(source).toContain('OutlineClassicPane')
    expect(source).toContain('OutlineDialogs')
  })

  it('PlanningInspector separates configured facts from current story state', () => {
    const source = read('components/planning/PlanningInspector.vue')
    expect(source).toContain('<h3>设定</h3>')
    expect(source).toContain('<h3>当前状态</h3>')
    expect(source).toContain('相关章节')
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

  it('PetBubbleStatusTab exposes factory command buttons', () => {
    const source = read('components/pet/PetBubbleStatusTab.vue')
    expect(source).toContain('factory-brief-box')
    expect(source).toContain('factoryCommands')
    expect(source).toContain('onFactoryIntent')
    expect(source).toContain('onFactoryRepair')
  })

  it('usePetBubbleView jumps to pipeline after factory repair', () => {
    const source = read('composables/usePetBubbleView.ts')
    expect(source).toContain("navigate('/workspace?focus=pipeline')")
    expect(source).toContain('auto_repair_chapter')
  })

  it('PetBubbleChatTab keeps welcome card modifier', () => {
    const source = read('components/pet/PetBubbleChatTab.vue')
    expect(source).toContain('welcome: index === 0 && msg.role')
    expect(source).toContain('msg-bubble.welcome')
  })

  it('ManuscriptInspector keeps context, AI, review, history, and settings together', () => {
    const source = read('components/manuscript/ManuscriptInspector.vue')
    expect(source).toContain('上下文')
    expect(source).toContain('采纳前不会修改正文')
    expect(source).toContain('修订历史')
    expect(source).toContain('阅读与排版')
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

  it('redirects legacy onboarding and trope routes into the unified create flow', () => {
    const source = read('router.ts')
    expect(source).toContain("redirect: '/create?welcome=1'")
    expect(source).toContain("redirect: '/create?source=template'")
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

  it('legacy chapter routes redirect into the manuscript center', () => {
    const source = read('router.ts')
    expect(source).toContain("{ path: '/chapters', redirect: '/writer'")
    expect(source).toContain("query: { chapter: String(to.params.id) }")
  })

  it('CreateWizard wires the four-step flow and three data-entry panes', () => {
    const source = read('views/CreateWizard.vue')
    expect(source).toContain('CREATE_STEPS')
    expect(source).toContain('确认建档并进入策划')
    expect(source).toContain('CreateQuickPane')
    expect(source).toContain('CreateParsePane')
    expect(source).toContain('CreateAiPane')
    expect(source).toContain('useCreateWizard')
  })

  it('CreateWizard scopes model blockers to the selected source', () => {
    const source = read('views/CreateWizard.vue')
    expect(source).toContain('modelBlocked')
    expect(source).toContain('快速输入和套路模板不受影响')
    expect(source).toContain('不会自动触发章节生成')
  })

  it('Dashboard stays a snapshot overview without direct generation controls', () => {
    const source = read('views/Dashboard.vue')
    expect(source).toContain('useProjectSnapshotStore')
    expect(source).toContain('项目健康')
    expect(source).toContain('安全的下一步')
    expect(source).not.toContain('submitChapter')
    expect(source).not.toContain('continueNovel')
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

  it('chapter maintenance stays in the production route', () => {
    const source = read('router.ts')
    expect(source).toContain("path: '/chapters/maintenance'")
    expect(source).toContain("navId: 'production'")
  })

  it('ChapterMaintenance shell wires repair queue and expand composable', () => {
    const source = read('views/ChapterMaintenance.vue')
    expect(source).toContain('useChapterMaintenance')
    expect(source).toContain('SemiAutoRepairHint')
    expect(source).toContain('PendingChaptersPanel')
    expect(source).toContain(':link-focus="true"')
    expect(source).toContain('BatchRunStatusBanner')
  })

  it('useChapterMaintenance expands pending panel on alerts query', () => {
    const source = read('composables/useChapterMaintenance.ts')
    expect(source).toContain("expand !== 'alerts'")
    expect(source).toContain('expandPendingPanel')
    expect(source).toContain('lastExpandedQuery')
  })

  it('App starts pending product tour after onboarding route transition', () => {
    const source = read('App.vue')
    expect(source).toContain('route.path')
    expect(source).toContain('maybeAutoStart')
    expect(source).toContain('isAppTourPending')
  })

  it('MonitorTabsPane wires LLM log viewer on logs tab', () => {
    const source = read('components/monitor/MonitorTabsPane.vue')
    expect(source).toContain('name="logs"')
    expect(source).toContain('LLMLogViewer')
    expect(source).toContain('费用与接口')
    const router = read('router.ts')
    expect(router.replace(/\s/g, '')).toContain("redirect:'/monitor?tab=logs'")
  })
})

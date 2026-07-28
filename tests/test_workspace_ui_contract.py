from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "web" / "frontend" / "src" / "views" / "WritingWorkspace.vue"
MANUSCRIPT_EDITOR = (
    ROOT / "web" / "frontend" / "src" / "components" / "manuscript" / "ManuscriptEditor.vue"
)
MANUSCRIPT_TREE = (
    ROOT / "web" / "frontend" / "src" / "components" / "manuscript" / "ManuscriptChapterTree.vue"
)
MANUSCRIPT_INSPECTOR = (
    ROOT / "web" / "frontend" / "src" / "components" / "manuscript" / "ManuscriptInspector.vue"
)
MANUSCRIPT_COMPOSABLE = (
    ROOT / "web" / "frontend" / "src" / "composables" / "useManuscriptWorkspace.ts"
)
ASSET_EDITOR = ROOT / "web" / "frontend" / "src" / "views" / "AssetEditor.vue"
ASSET_EDITOR_PANEL = (
    ROOT / "web" / "frontend" / "src" / "components" / "asset" / "AssetEditorPanel.vue"
)
ASSET_EDITOR_COMPOSABLE = ROOT / "web" / "frontend" / "src" / "composables" / "useAssetEditor.ts"
ASSET_LIST_SIDEBAR = (
    ROOT / "web" / "frontend" / "src" / "components" / "asset" / "AssetListSidebar.vue"
)
MARKDOWN_EDITOR = ROOT / "web" / "frontend" / "src" / "components" / "MarkdownAssetEditor.vue"
DASHBOARD = ROOT / "web" / "frontend" / "src" / "views" / "Dashboard.vue"
APP = ROOT / "web" / "frontend" / "src" / "App.vue"
APP_SHELL = ROOT / "web" / "frontend" / "src" / "app" / "shell" / "AppShell.vue"
APP_SIDEBAR = ROOT / "web" / "frontend" / "src" / "app" / "shell" / "AppSidebar.vue"
DESKTOP_LIFECYCLE = (
    ROOT / "web" / "frontend" / "src" / "app" / "bootstrap" / "useDesktopLifecycle.ts"
)
FRONTEND_MAIN = ROOT / "web" / "frontend" / "src" / "main.ts"
PET_BUBBLE = ROOT / "web" / "frontend" / "src" / "views" / "PetBubbleView.vue"
PET_BUBBLE_STATUS = (
    ROOT / "web" / "frontend" / "src" / "components" / "pet" / "PetBubbleStatusTab.vue"
)
PET_BUBBLE_CHAT = (
    ROOT / "web" / "frontend" / "src" / "components" / "pet" / "PetBubbleChatTab.vue"
)
PET_BUBBLE_VIEW = ROOT / "web" / "frontend" / "src" / "composables" / "usePetBubbleView.ts"
LLM_CONFIG = ROOT / "web" / "frontend" / "src" / "components" / "LLMConfig.vue"
PRODUCTION_CENTER = ROOT / "web" / "frontend" / "src" / "views" / "ProductionCenter.vue"
PRODUCTION_TASKS = (
    ROOT / "web" / "frontend" / "src" / "components" / "production" / "ProductionTaskWorkspace.vue"
)
PRODUCTION_REVIEWS = (
    ROOT / "web" / "frontend" / "src" / "components" / "production" / "ProductionReviewWorkspace.vue"
)
PRODUCTION_COSTS = (
    ROOT / "web" / "frontend" / "src" / "components" / "production" / "ProductionCostPanel.vue"
)
PRODUCTION_LOGS = (
    ROOT / "web" / "frontend" / "src" / "components" / "production" / "ProductionLogsPanel.vue"
)
CONFIG_SECTIONS_STACK = (
    ROOT / "web" / "frontend" / "src" / "components" / "config" / "ConfigSectionsStack.vue"
)
PET_WINDOW_INTERACTION = (
    ROOT / "web" / "frontend" / "src" / "composables" / "usePetWindowInteraction.ts"
)

OUTLINE_VIEW = ROOT / "web" / "frontend" / "src" / "views" / "OutlineView.vue"
OUTLINE_EDITOR = ROOT / "web" / "frontend" / "src" / "views" / "OutlineEditor.vue"
PLANNING_TREE = (
    ROOT / "web" / "frontend" / "src" / "components" / "planning" / "PlanningEntityTree.vue"
)
PLANNING_CANVAS = (
    ROOT / "web" / "frontend" / "src" / "components" / "planning" / "PlanningCanvas.vue"
)
PLANNING_INSPECTOR = (
    ROOT / "web" / "frontend" / "src" / "components" / "planning" / "PlanningInspector.vue"
)
CREATE_WIZARD = ROOT / "web" / "frontend" / "src" / "views" / "CreateWizard.vue"
CREATE_FLOW = ROOT / "web" / "frontend" / "src" / "features" / "create" / "createFlow.ts"
ROUTER = ROOT / "web" / "frontend" / "src" / "router.ts"
CONFIG_VIEW = ROOT / "web" / "frontend" / "src" / "views" / "ConfigView.vue"
LIBRARY_VIEW = ROOT / "web" / "frontend" / "src" / "views" / "LibraryView.vue"
LIBRARY_BOOK_GRID = (
    ROOT / "web" / "frontend" / "src" / "components" / "library" / "LibraryBookGrid.vue"
)
LIBRARY_PROJECTS = ROOT / "web" / "frontend" / "src" / "composables" / "useLibraryProjects.ts"
STATE_VIEW = ROOT / "web" / "frontend" / "src" / "views" / "StateView.vue"
STATE_SETTINGS_TAB = (
    ROOT / "web" / "frontend" / "src" / "components" / "state" / "StateSettingsTab.vue"
)
STATE_CHRONICLE_TAB = (
    ROOT / "web" / "frontend" / "src" / "components" / "state" / "StateChronicleTab.vue"
)
OUTLINE_GENES = (
    ROOT / "web" / "frontend" / "src" / "components" / "outline" / "OutlineGenesPanel.vue"
)
OUTLINE_MINDMAP = (
    ROOT / "web" / "frontend" / "src" / "components" / "outline" / "OutlineMindmapPane.vue"
)
PLUGIN_MANAGER = ROOT / "web" / "frontend" / "src" / "views" / "PluginManager.vue"
PLUGIN_GRID = ROOT / "web" / "frontend" / "src" / "components" / "plugin" / "PluginGrid.vue"
PLUGIN_MANAGER_COMPOSABLE = ROOT / "web" / "frontend" / "src" / "composables" / "usePluginManager.ts"
SHARED_EMPTY_STATE = ROOT / "web" / "frontend" / "src" / "shared" / "ui" / "EmptyState.vue"
NOVEL_PROGRESS_HELP = ROOT / "web" / "frontend" / "src" / "components" / "NovelProgressHelp.vue"
EMBEDDING_CONFIG = ROOT / "web" / "frontend" / "src" / "components" / "EmbeddingConfig.vue"
PIPELINE_RUNTIME = ROOT / "web" / "frontend" / "src" / "components" / "PipelineRuntimeConfig.vue"
SHANSHAN_COPY = ROOT / "web" / "frontend" / "src" / "constants" / "shanshanCopy.ts"
FRONTEND_API = ROOT / "web" / "frontend" / "src" / "api.ts"
FRONTEND_API_CLIENT = ROOT / "web" / "frontend" / "src" / "api" / "client.ts"
BUBBLE_WINDOW = ROOT / "web" / "frontend" / "electron" / "windows" / "bubble-window.ts"


def test_writer_uses_revisioned_autosave_and_confirmed_ai_suggestions() -> None:
    writer_source = WRITER.read_text(encoding="utf-8")
    composable_source = MANUSCRIPT_COMPOSABLE.read_text(encoding="utf-8")

    assert "useManuscriptWorkspace" in writer_source
    assert "confirmAiIntent" in writer_source
    assert "采纳建议" in MANUSCRIPT_INSPECTOR.read_text(encoding="utf-8")
    assert "expected_revision" in (
        ROOT / "web" / "frontend" / "src" / "api" / "manuscript.ts"
    ).read_text(encoding="utf-8")
    assert "conflictDocument" in composable_source
    assert "window.setTimeout" in composable_source


def test_writer_save_button_uses_toolbar_style_instead_of_green_block() -> None:
    source = WRITER.read_text(encoding="utf-8")
    assert 'type="success"\n              size="default"\n              icon="DocumentChecked"\n              class="premium-btn btn-save"' not in source
    assert "linear-gradient(135deg, #16a34a, #65a30d)" not in source


def test_writer_uses_tiptap_json_instead_of_a_textarea() -> None:
    source = MANUSCRIPT_EDITOR.read_text(encoding="utf-8")

    assert "@tiptap/vue-3" in source
    assert "StarterKit" in source
    assert "instance.getJSON()" in source
    assert "<textarea" not in source


def test_asset_source_panels_are_hidden_until_toolbar_toggle() -> None:
    asset_shell = ASSET_EDITOR.read_text(encoding="utf-8")
    asset_panel = ASSET_EDITOR_PANEL.read_text(encoding="utf-8")
    markdown_source = MARKDOWN_EDITOR.read_text(encoding="utf-8")

    assert "showAssetSource" in asset_shell or "showAssetSource" in asset_panel
    assert "@click=\"showAssetSource = !showAssetSource\"" in asset_panel
    assert ":show-source=\"showAssetSource\"" in asset_panel
    assert "showSource?: boolean" in markdown_source
    assert 'v-if="showSource"' in markdown_source


def test_asset_editor_shell_delegates_to_subcomponents() -> None:
    source = ASSET_EDITOR.read_text(encoding="utf-8")
    assert "AssetListSidebar" in source
    assert "AssetEditorPanel" in source
    assert "AssetEditorDialogs" in source
    assert "useAssetEditor" in source


def test_asset_list_sidebar_keeps_custom_asset_actions() -> None:
    source = ASSET_LIST_SIDEBAR.read_text(encoding="utf-8")
    assert "导入名词解释" in source
    assert "onBulkImportToTerminology" in source
    assert "onContextCommand" in source


def test_dashboard_uses_snapshot_without_direct_generation() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "useProjectSnapshotStore" in source
    assert "snapshot.next_actions" in source
    assert "confirm: '1'" in source
    assert "continueNovel" not in source
    assert "submitChapter" not in source


def test_create_view_exposes_four_step_flow_and_legacy_redirect() -> None:
    source = CREATE_WIZARD.read_text(encoding="utf-8")
    flow = CREATE_FLOW.read_text(encoding="utf-8")
    router = ROUTER.read_text(encoding="utf-8")
    assert "CREATE_STEPS" in source
    assert "['工作方式', '素材来源', '写作规格', '确认建档']" in flow
    assert "{ id: 'quick'" in source
    assert "{ id: 'ai'" in source
    assert "{ id: 'parse'" in source
    assert "{ id: 'template'" in source
    assert "redirect: '/create?welcome=1'" in router


def test_library_view_exposes_studio_tab() -> None:
    source = (ROOT / "web" / "frontend" / "src" / "views" / "LibraryView.vue").read_text(encoding="utf-8")
    assert "StudioProductionBoard" in source
    assert "制片看板" in source
    assert "importDemoProject" in source
    assert "importingDemo" in source


def test_dashboard_exposes_snapshot_health_and_safe_next_actions() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    assert "项目健康" in dashboard
    assert "安全的下一步" in dashboard
    assert "authoritative_completed" in dashboard
    assert "<el-progress" in dashboard
    assert "planning?.counts" in dashboard
    assert "blockingIssues" in dashboard


def test_pet_abort_button_uses_short_label() -> None:
    bubble_source = PET_BUBBLE.read_text(encoding="utf-8")
    status_source = PET_BUBBLE_STATUS.read_text(encoding="utf-8")
    source = bubble_source + status_source
    assert "中止当前章节生成" not in source
    assert ">中止<" in source.replace("\n", "").replace(" ", "")


def test_shanshan_status_does_not_repeat_work_progress_line() -> None:
    source = PET_BUBBLE_STATUS.read_text(encoding="utf-8")
    assert 'class="status-detail-desc"' in source
    assert "work-progress-line" not in source
    assert "pet.workProgressLine" not in source


def test_shanshan_chat_keeps_four_suggested_questions() -> None:
    source = SHANSHAN_COPY.read_text(encoding="utf-8")
    array_body = source.split("SHANSHAN_SUGGESTED_QUESTIONS = [", 1)[1].split("] as const", 1)[0]
    questions = [line.strip() for line in array_body.splitlines() if line.strip().startswith("'")]
    assert len(questions) == 4


def test_library_book_cards_use_compact_comparison_layout_and_one_menu() -> None:
    source = LIBRARY_BOOK_GRID.read_text(encoding="utf-8")
    assert 'class="project-cover"' in source
    assert 'class="project-meta"' in source
    assert source.count("@command=") == 1
    assert 'command="rename"' in source
    assert 'command="export-docx"' in source
    assert "book-spine" not in source


def test_project_manager_uses_cached_pipeline_alert_count() -> None:
    source = (ROOT / "web" / "project_manager.py").read_text(encoding="utf-8")
    assert "count_pipeline_alerts_cached" in source


def test_library_cards_show_pending_alert_badge() -> None:
    grid_source = LIBRARY_BOOK_GRID.read_text(encoding="utf-8")
    projects_source = LIBRARY_PROJECTS.read_text(encoding="utf-8")
    assert "pending_alert_count" in grid_source
    assert 'class="risk-link"' in grid_source
    assert "未解决风险" in grid_source
    assert "openPendingMaintenance" in projects_source
    assert "/production?tab=reviews" in projects_source


def test_empty_state_panel_used_in_key_views() -> None:
    library = LIBRARY_VIEW.read_text(encoding="utf-8")
    tasks = PRODUCTION_TASKS.read_text(encoding="utf-8")
    reviews = PRODUCTION_REVIEWS.read_text(encoding="utf-8")
    assert "shared/ui/EmptyState.vue" in library
    assert "尚无生产任务" in tasks
    assert "没有匹配的审校问题" in reviews
    assert 'class="ui-empty-state"' in SHARED_EMPTY_STATE.read_text(encoding="utf-8")


def test_dashboard_exposes_authoritative_progress_bar() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "authoritative_completed" in source
    assert "target_chapters" in source
    assert "<el-progress" in source


def test_manuscript_tree_virtualizes_and_filters_chapters() -> None:
    source = MANUSCRIPT_TREE.read_text(encoding="utf-8")
    assert "useVirtualizer" in source
    assert "搜索章节" in source
    assert "需处理" in source
    assert "getItemKey" in source


def test_production_center_includes_canonical_cost_panel() -> None:
    shell_source = PRODUCTION_CENTER.read_text(encoding="utf-8")
    costs_source = PRODUCTION_COSTS.read_text(encoding="utf-8")
    assert "ProductionCostPanel" in shell_source
    assert "summary.persisted" in costs_source
    assert "persisted_error" in costs_source


def test_production_tasks_unify_queue_timeline_and_logs() -> None:
    source = PRODUCTION_TASKS.read_text(encoding="utf-8")
    assert "运行与队列" in source
    assert "状态时间线" in source
    assert "任务日志" in source
    assert "useVirtualizer" in source


def test_production_reviews_have_filter_tabs() -> None:
    source = PRODUCTION_REVIEWS.read_text(encoding="utf-8")
    assert "筛选审校问题" in source
    assert "filterProductionReviews" in source
    assert "外审" in source


def test_app_shows_backend_offline_alert() -> None:
    shell_source = APP_SHELL.read_text(encoding="utf-8")
    lifecycle_source = DESKTOP_LIFECYCLE.read_text(encoding="utf-8")
    assert "backend-offline-alert" in shell_source
    assert "栖墨后台未响应" in shell_source
    assert "HEALTH_FAIL_THRESHOLD" in lifecycle_source


def test_batch_dialog_blocks_submit_when_external_review_active() -> None:
    dialog = (
        ROOT / "web" / "frontend" / "src" / "components" / "NovelBatchRunDialog.vue"
    ).read_text(encoding="utf-8")
    composable = (
        ROOT / "web" / "frontend" / "src" / "composables" / "useNovelBatchRun.ts"
    ).read_text(encoding="utf-8")
    assert "isExternalBlockActive" in composable
    assert "isExternalBlockActive" in dialog


def test_production_reviews_scope_bulk_actions_to_compatible_items() -> None:
    source = PRODUCTION_REVIEWS.read_text(encoding="utf-8")
    assert "resolveReviewActionTargets" in source
    assert "compatibleCount" in source
    assert "批量修复动作" in source


def test_production_cost_panel_handles_load_error() -> None:
    source = PRODUCTION_COSTS.read_text(encoding="utf-8")
    assert "persisted_error" in source
    assert "cost-warning" in source


def test_legacy_chapter_routes_converge_on_manuscript_center() -> None:
    source = ROUTER.read_text(encoding="utf-8")
    assert "{ path: '/chapters', redirect: '/writer'" in source
    assert "{ path: '/chapters/list', redirect: '/writer'" in source
    assert "query: { chapter: String(to.params.id) }" in source
    assert "ChapterList.vue" not in source
    assert "ChapterDetail.vue" not in source


def test_embedding_config_stays_collapsed_by_default() -> None:
    source = EMBEDDING_CONFIG.read_text(encoding="utf-8")
    assert "const expanded = ref(false)" in source
    assert "long_form_vector_recommended" in source


def test_api_errors_prefer_backend_detail_over_status_text() -> None:
    api_source = FRONTEND_API.read_text(encoding="utf-8")
    if FRONTEND_API_CLIENT.is_file():
        api_source = FRONTEND_API_CLIENT.read_text(encoding="utf-8") + "\n" + api_source
    library_source = LIBRARY_PROJECTS.read_text(encoding="utf-8")
    manuscript_source = MANUSCRIPT_COMPOSABLE.read_text(encoding="utf-8")

    assert "export const apiErrorMessage" in api_source
    assert "error?.response?.data?.detail" in api_source
    assert "error?.response?.status" in api_source
    assert "Request failed with status code" in api_source
    assert "error.message = message" in api_source
    assert "apiErrorMessage(error" in library_source
    assert "error instanceof Error ? error.message" in manuscript_source


def test_electron_api_auth_does_not_use_native_prompt() -> None:
    source = FRONTEND_API_CLIENT.read_text(encoding="utf-8")

    assert "window.prompt" not in source
    assert "ElMessageBox.prompt" not in source
    assert "需要访问令牌" not in source
    assert "请输入栖墨远程访问令牌" not in source
    assert "fetchLocalAccessToken" in source
    assert "X-Novel-Agent-Local-Client" in source
    assert "localStorage.getItem('novel-agent-access-token')) return" not in source


def test_pet_bubble_initial_position_is_clamped_to_work_area() -> None:
    source = BUBBLE_WINDOW.read_text(encoding="utf-8")
    create_block = source.split("export function createBubbleWindow", 1)[1].split(
        "const bubbleWindow = new BrowserWindow",
        1,
    )[0]

    assert "workArea.x + workArea.width - width" in create_block
    assert "workArea.y + workArea.height - height" in create_block
    assert "Math.min(" in create_block


def test_production_center_uses_manual_refresh_and_shared_polling() -> None:
    source = PRODUCTION_CENTER.read_text(encoding="utf-8")
    composable = (
        ROOT / "web" / "frontend" / "src" / "composables" / "useProductionWorkspace.ts"
    ).read_text(encoding="utf-8")
    assert "Refresh" in source
    assert '@click="load()"' in source
    assert "subscribePolling" in composable
    assert "window.setInterval" not in composable


def test_sidebar_brand_uses_single_line_inkrest_lockup() -> None:
    source = APP_SIDEBAR.read_text(encoding="utf-8")
    compact = "".join(source.split())
    assert 'class="brand__copy"' in source
    assert "<span><strong>栖墨</strong><em>INKREST</em></span>" in compact
    assert "<small>本地长篇创作空间</small>" in source


def test_llm_config_exposes_daily_and_reasoning_tier_selectors() -> None:
    source = LLM_CONFIG.read_text(encoding="utf-8")
    assert "daily_model_id" in source
    assert "reasoning_model_id" in source
    assert "role_tiers" in source


def test_pet_monitor_navigation_uses_short_label() -> None:
    status_source = PET_BUBBLE_STATUS.read_text(encoding="utf-8")
    composable_source = PET_BUBBLE_VIEW.read_text(encoding="utf-8")
    source = status_source + composable_source
    assert "<span>🔧 修章</span>" in source
    assert "navigate('/production?tab=reviews')" in composable_source
    assert "onNavigate('/production?tab=reviews')" in status_source
    assert "<span>📊 运行监控</span>" not in source


def test_production_workspace_fills_remaining_viewport_height() -> None:
    center_source = PRODUCTION_CENTER.read_text(encoding="utf-8")
    task_source = PRODUCTION_TASKS.read_text(encoding="utf-8")
    log_source = PRODUCTION_LOGS.read_text(encoding="utf-8")

    assert "height: 100%;" in center_source
    assert "min-height: 0;" in center_source
    assert "height: 100%;" in task_source
    assert "height: 100%;" in log_source


def test_settings_page_applies_shared_fold_card_alignment() -> None:
    config_source = CONFIG_VIEW.read_text(encoding="utf-8")
    runtime_source = PIPELINE_RUNTIME.read_text(encoding="utf-8")

    assert ".config-page :deep(.fold-head)" in config_source
    assert ".config-page :deep(.fold-body)" in config_source
    assert ".fold-card {" not in runtime_source


def test_production_center_exposes_review_queue_and_confirmation() -> None:
    center = PRODUCTION_CENTER.read_text(encoding="utf-8")
    reviews = PRODUCTION_REVIEWS.read_text(encoding="utf-8")
    dialog = (
        ROOT / "web" / "frontend" / "src" / "components" / "production" / "ProductionActionDialog.vue"
    ).read_text(encoding="utf-8")
    assert "ProductionReviewWorkspace" in center
    assert "审校与修复" in reviews
    assert "重跑门禁" in reviews
    assert "只有点击下方确认按钮后才会提交" in dialog


def test_chapter_maintenance_redirects_to_unified_production_route() -> None:
    router_source = ROUTER.read_text(encoding="utf-8")

    assert "path: '/chapters/maintenance'" in router_source
    assert "path: '/production', query: { tab: 'reviews' }" in router_source
    assert "ChapterMaintenance.vue" not in router_source


def test_tasks_store_uses_polling_reference_counts() -> None:
    tasks_source = (ROOT / "web" / "frontend" / "src" / "stores" / "tasks.ts").read_text(
        encoding="utf-8"
    )
    transport_source = (
        ROOT / "web" / "frontend" / "src" / "composables" / "useTaskProgress.ts"
    ).read_text(encoding="utf-8")
    production_source = (
        ROOT / "web" / "frontend" / "src" / "composables" / "useProductionWorkspace.ts"
    ).read_text(encoding="utf-8")

    assert "createTaskListTransport" in tasks_source
    assert "createRuntimeLogTransport" in tasks_source
    assert "consumers" in transport_source
    assert "wsAllowReconnect" in transport_source
    assert "subscribePolling" in production_source


def test_tasks_store_exposes_failure_action_contract() -> None:
    tasks_source = (ROOT / "web" / "frontend" / "src" / "stores" / "tasks.ts").read_text(
        encoding="utf-8"
    )
    client_source = (ROOT / "web" / "frontend" / "src" / "api" / "client.ts").read_text(
        encoding="utf-8"
    )

    assert "retryable?: boolean" in tasks_source
    assert "user_action?: string" in tasks_source
    assert "resumable_from?: string" in tasks_source
    assert "status_reason?: string" in tasks_source
    assert "normalizeFailureDetail" in tasks_source
    assert "normalizeFailureDetail" in client_source
    assert "formatFailureDetail" in client_source


def test_manuscript_composable_guards_save_and_conflict_races() -> None:
    source = MANUSCRIPT_COMPOSABLE.read_text(encoding="utf-8")

    assert "expected_revision: current.revision" in source
    assert "snapshot === JSON.stringify(content.value)" in source
    assert "conflictDocument.value" in source
    assert "keepLocalAsNewRevision" in source


def test_production_logs_tab_wires_viewer() -> None:
    logs_source = PRODUCTION_LOGS.read_text(encoding="utf-8")
    router_source = (ROOT / "web" / "frontend" / "src" / "router.ts").read_text(encoding="utf-8")

    assert "ProductionRuntimeLog" in logs_source
    assert "LLMLogViewer" in logs_source
    compact_router = router_source.replace(" ", "").replace("'", '"')
    assert 'path:"/logs",redirect:{path:"/production",query:{tab:"logs"}}' in compact_router


def test_production_page_is_the_single_operations_center() -> None:
    source = PRODUCTION_CENTER.read_text(encoding="utf-8")
    compact = source.replace("\n", "").replace(" ", "")
    assert ">生产中心<" in compact
    assert "运行、审校修复、费用与日志" in source
    assert "ProductionTaskWorkspace" in source
    assert "ProductionReviewWorkspace" in source


def test_production_pause_banner_prioritizes_repair_before_resume() -> None:
    source = PRODUCTION_CENTER.read_text(encoding="utf-8")
    assert "处理待修章节" in source
    assert "仍要继续" in source
    assert "useNovelBatchRun" in source
    assert "batchPaused" in source
    assert "pauseReason" in source


def test_novel_progress_help_includes_dual_audit_footnote() -> None:
    source = (
        ROOT / "web" / "frontend" / "src" / "components" / "NovelProgressHelp.vue"
    ).read_text(encoding="utf-8")
    assert "INTERNAL_GATE_HINT" in source
    assert "EXTERNAL_AUDIT_HINT" in source


def test_e2e_fixture_route_gated_by_env() -> None:
    app_source = (ROOT / "web" / "app.py").read_text(encoding="utf-8")
    assert "E2E_FIXTURES" in app_source
    assert "e2e_fixtures_router" in app_source


def test_dual_audit_copy_splits_internal_and_external() -> None:
    source = (
        ROOT / "web" / "frontend" / "src" / "constants" / "repairWorkflow.ts"
    ).read_text(encoding="utf-8")
    inspector = MANUSCRIPT_INSPECTOR.read_text(encoding="utf-8")
    assert "INTERNAL_GATE_HINT" in source
    assert "EXTERNAL_AUDIT_HINT" in source
    assert "流水线门禁" in inspector
    assert "Phase 5 审校中心" in inspector


def test_production_tasks_and_pet_localize_task_steps() -> None:
    task_source = PRODUCTION_TASKS.read_text(encoding="utf-8")
    pet_source = (ROOT / "web" / "frontend" / "src" / "stores" / "pet.ts").read_text(
        encoding="utf-8"
    )
    production_labels = (
        ROOT / "web" / "frontend" / "src" / "entities" / "production" / "production.ts"
    ).read_text(encoding="utf-8")
    assert "productionStepLabel" in task_source
    assert "formatTaskStep" in pet_source
    assert "writer: '正文写作'" in production_labels


def test_llm_log_viewer_fills_remaining_height() -> None:
    source = (
        ROOT / "web" / "frontend" / "src" / "components" / "LLMLogViewer.vue"
    ).read_text(encoding="utf-8")
    assert "log-table-region" in source
    assert 'max-height="520"' not in source


def test_outline_page_places_progress_help_above_queue_status() -> None:
    source = OUTLINE_EDITOR.read_text(encoding="utf-8")
    template = source.split("<template>", 1)[1]
    help_idx = template.index("<NovelProgressHelp")
    queue_idx = template.index("<OutlineQueueStatus")
    assert help_idx < queue_idx


def test_progress_help_and_production_use_canonical_progress_sources() -> None:
    help_source = NOVEL_PROGRESS_HELP.read_text(encoding="utf-8")
    production_source = PRODUCTION_CENTER.read_text(encoding="utf-8")
    assert "useNovelProgress" in help_source
    assert "snapshot.chapter_progress" in production_source
    assert "getNovelBatchStatus" not in help_source


def test_shanshan_copy_points_to_production_center() -> None:
    source = SHANSHAN_COPY.read_text(encoding="utf-8")
    assert "生产中心" in source
    assert "章节维护" not in source
    assert "运行监控" not in source


def test_readme_documents_current_entrypoints() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "python -m pytest" in readme
    assert "python main.py serve" in readme
    assert "electron:pack" in readme
    assert "栖墨.exe" in readme
    assert "python -m unittest tests.test_pipeline" not in readme


def test_batch_run_dialog_is_global_and_dashboard_only_routes_intents() -> None:
    app_source = APP.read_text(encoding="utf-8")
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    assert "NovelBatchRunDialog" in app_source
    assert "NovelBatchRunDialog" not in dashboard
    assert "confirm: '1'" in dashboard
    assert "continueNovel" not in dashboard


def test_longform_vector_warn_surfaces_in_readiness_and_dialog() -> None:
    readiness = (ROOT / "web" / "frontend" / "src" / "utils" / "projectReadiness.ts").read_text(
        encoding="utf-8"
    )
    dialog = (ROOT / "web" / "frontend" / "src" / "components" / "NovelBatchRunDialog.vue").read_text(
        encoding="utf-8"
    )
    assert "longFormVectorWarn" in readiness
    assert "showVectorAlert" in dialog
    assert "LONG_FORM_VECTOR_WARN_TEXT" in dialog


def test_vector_readiness_and_task_queue_wired_in_batch_run() -> None:
    batch_run = (
        ROOT / "web" / "frontend" / "src" / "composables" / "useNovelBatchRun.ts"
    ).read_text(encoding="utf-8")
    production_tasks = PRODUCTION_TASKS.read_text(encoding="utf-8")
    readiness = (ROOT / "web" / "frontend" / "src" / "utils" / "projectReadiness.ts").read_text(
        encoding="utf-8"
    )
    assert "readinessCanContinue" in readiness
    assert "mergeServerReadinessPending" in readiness
    assert "resolveVectorContextFromApis" in batch_run
    assert "readinessCanContinue" in batch_run
    assert "serverReadiness" in batch_run
    assert "vectorReadiness" in batch_run
    assert "运行与队列" in production_tasks
    assert "filterProductionTasks" in production_tasks


def test_batch_run_cost_uses_model_pricing_hint() -> None:
    estimate = ROOT / "web" / "frontend" / "src" / "utils" / "tokenCostEstimate.ts"
    composable = ROOT / "web" / "frontend" / "src" / "composables" / "useNovelBatchRun.ts"
    assert "blended_price_per_1k_cny" in estimate.read_text(encoding="utf-8")
    assert "resolveDailyModelPricePer1k" in composable.read_text(encoding="utf-8")


def test_batch_run_form_persists_per_project() -> None:
    batch_form = ROOT / "web" / "frontend" / "src" / "utils" / "batchRunForm.ts"
    composable = ROOT / "web" / "frontend" / "src" / "composables" / "useNovelBatchRun.ts"
    dialog = ROOT / "web" / "frontend" / "src" / "components" / "NovelBatchRunDialog.vue"
    form_source = batch_form.read_text(encoding="utf-8")
    assert "inkrest_batch_form_" in form_source
    assert "loadSavedBatchForm" in composable.read_text(encoding="utf-8")
    assert "saveBatchForm" in composable.read_text(encoding="utf-8")
    assert "cancelBatchRunMessage" in form_source
    assert "busyPhaseLabel" in dialog.read_text(encoding="utf-8")


def test_shanshan_chat_opens_with_compact_editor_welcome_card() -> None:
    bubble_source = PET_BUBBLE.read_text(encoding="utf-8")
    chat_source = PET_BUBBLE_CHAT.read_text(encoding="utf-8")
    copy_source = SHANSHAN_COPY.read_text(encoding="utf-8")

    assert "PetBubbleChatTab" in bubble_source
    assert ":class=\"{ welcome: index === 0 && msg.role === 'assistant' }\"" in chat_source
    assert ".chat-row.assistant .msg-bubble.welcome" in chat_source
    assert "结合当前作品体量与门禁摘要排障" in copy_source
    assert "嗨，我是山山，栖墨里的驻场小编辑。" in copy_source
    assert "查任务进度、体量与已写章数" in copy_source
    assert "门禁摘要" in copy_source
    assert "生产中心" in copy_source
    assert "正文" in copy_source
    assert "你现在想先处理哪一件？" in copy_source
    assert "'全书暂停了，怎么续跑？'" in copy_source
    assert "'日常档和逻辑档怎么选？'" in copy_source


def test_writer_shell_delegates_to_subcomponents() -> None:
    source = WRITER.read_text(encoding="utf-8")
    assert "ManuscriptChapterTree" in source
    assert "ManuscriptEditor" in source
    assert "ManuscriptInspector" in source
    assert "Splitpanes" in source


def test_writer_chapter_tree_supports_search_status_and_selection() -> None:
    source = MANUSCRIPT_TREE.read_text(encoding="utf-8")
    assert "章节目录" in source
    assert "搜索章节" in source
    assert "status.value" in source
    assert "emit('select'" in source


def test_state_view_shell_delegates_to_tab_components() -> None:
    source = STATE_VIEW.read_text(encoding="utf-8")
    assert "StateSettingsTab" in source
    assert "StateChronicleTab" in source


def test_state_chronicle_tab_keeps_relation_graph_contract() -> None:
    source = STATE_CHRONICLE_TAB.read_text(encoding="utf-8")
    assert "NODE_CIRCLE_R" in source
    assert "RELATION_TYPE_COLORS" in source
    assert "relations-svg" in source


def test_state_settings_tab_keeps_foreshadow_collect() -> None:
    source = STATE_SETTINGS_TAB.read_text(encoding="utf-8")
    assert "伏笔债务" in source
    assert "onCollect" in source
    assert "强行催收" in source


def test_outline_shell_delegates_to_pane_components() -> None:
    source = OUTLINE_VIEW.read_text(encoding="utf-8")
    assert "Splitpanes" in source
    assert "PlanningEntityTree" in source
    assert "PlanningCanvas" in source
    assert "PlanningInspector" in source
    assert "OutlineEditor" in source
    assert "OutlineEditorLegacy" not in source
    inspector = PLANNING_INSPECTOR.read_text(encoding="utf-8")
    assert "设定" in inspector
    assert "当前状态" in inspector


def test_outline_genes_panel_exposes_edit_action() -> None:
    source = OUTLINE_GENES.read_text(encoding="utf-8")
    assert "类型基因" in source
    assert "onOpenEditGenes" in source


def test_outline_mindmap_pane_exposes_canvas() -> None:
    source = OUTLINE_MINDMAP.read_text(encoding="utf-8")
    assert "mindmap-canvas" in source
    assert "setNodeRef" in source


def test_plugin_manager_shell_delegates_to_subcomponents() -> None:
    source = PLUGIN_MANAGER.read_text(encoding="utf-8")
    composable_source = PLUGIN_MANAGER_COMPOSABLE.read_text(encoding="utf-8")
    assert "PluginMetricsCards" in source
    assert "PluginFilterBar" in source
    assert "PluginGrid" in source
    assert "PluginManagerDialogs" in source
    assert "usePluginManager" in source
    assert "PluginAuthorHelpDialog" in source
    assert "trustPlugin" in composable_source
    assert "installPluginZip" in composable_source


def test_plugin_grid_keeps_trust_toggle_actions() -> None:
    source = PLUGIN_GRID.read_text(encoding="utf-8")
    assert "status-indicator" in source
    assert "待信任" in source
    assert "onToggle" in source
    assert "onTrust" in source
    assert "requires_reauthorization" in source
    assert "onDelete" in source


def test_trope_entry_is_folded_into_the_create_wizard() -> None:
    router = ROUTER.read_text(encoding="utf-8")
    wizard = CREATE_WIZARD.read_text(encoding="utf-8")
    quick_form = (ROOT / "web" / "frontend" / "src" / "components" / "QuickCreateForm.vue").read_text(
        encoding="utf-8"
    )
    assert "redirect: '/create?source=template'" in router
    assert "{ id: 'template'" in wizard
    assert "PresetSelector" in quick_form


def test_config_view_shell_delegates_to_nav_and_sections() -> None:
    shell_source = CONFIG_VIEW.read_text(encoding="utf-8")
    stack_source = CONFIG_SECTIONS_STACK.read_text(encoding="utf-8")
    assert "ConfigPageNav" in shell_source
    assert "ConfigSectionsStack" in shell_source
    assert "useConfigNavigation" in shell_source
    assert "LLMConfig" in stack_source
    assert "EmbeddingConfig" in stack_source


def test_production_shell_delegates_to_workspace_panels() -> None:
    shell_source = PRODUCTION_CENTER.read_text(encoding="utf-8")
    composable_source = (
        ROOT / "web" / "frontend" / "src" / "composables" / "useProductionWorkspace.ts"
    ).read_text(encoding="utf-8")
    assert "ProductionTaskWorkspace" in shell_source
    assert "ProductionReviewWorkspace" in shell_source
    assert "getProductionWorkspace" in composable_source


def test_pet_view_shell_delegates_to_window_interaction() -> None:
    shell_source = (ROOT / "web" / "frontend" / "src" / "views" / "PetView.vue").read_text(
        encoding="utf-8"
    )
    interaction_source = PET_WINDOW_INTERACTION.read_text(encoding="utf-8")
    assert "usePetWindowInteraction" in shell_source
    assert "PetSprite" in shell_source
    assert "togglePetBubble" in interaction_source
    assert "applyEdgeDockIfNeeded" in interaction_source

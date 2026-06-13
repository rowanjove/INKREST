from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "web" / "frontend" / "src" / "views" / "WritingWorkspace.vue"
WRITER_EDITOR_MAIN = (
    ROOT / "web" / "frontend" / "src" / "components" / "writing" / "WritingEditorMain.vue"
)
WRITER_CHAPTER = (
    ROOT / "web" / "frontend" / "src" / "composables" / "useWritingChapterEditor.ts"
)
WRITER_AI_WRITE = ROOT / "web" / "frontend" / "src" / "composables" / "useWritingAiWrite.ts"
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
DASHBOARD_SERIAL = (
    ROOT / "web" / "frontend" / "src" / "composables" / "useDashboardSerial.ts"
)
DASHBOARD_SERIALIZATION_PANE = (
    ROOT / "web" / "frontend" / "src" / "components" / "dashboard" / "DashboardSerializationPane.vue"
)
APP = ROOT / "web" / "frontend" / "src" / "App.vue"
PET_BUBBLE = ROOT / "web" / "frontend" / "src" / "views" / "PetBubbleView.vue"
PET_BUBBLE_STATUS = (
    ROOT / "web" / "frontend" / "src" / "components" / "pet" / "PetBubbleStatusTab.vue"
)
PET_BUBBLE_CHAT = (
    ROOT / "web" / "frontend" / "src" / "components" / "pet" / "PetBubbleChatTab.vue"
)
PET_BUBBLE_VIEW = ROOT / "web" / "frontend" / "src" / "composables" / "usePetBubbleView.ts"
TASK_LOG = ROOT / "web" / "frontend" / "src" / "components" / "TaskLog.vue"
LLM_CONFIG = ROOT / "web" / "frontend" / "src" / "components" / "LLMConfig.vue"
LOG_STREAM = ROOT / "web" / "frontend" / "src" / "components" / "LogStream.vue"
MONITOR = ROOT / "web" / "frontend" / "src" / "views" / "MonitorView.vue"
MONITOR_TABS = (
    ROOT / "web" / "frontend" / "src" / "components" / "monitor" / "MonitorTabsPane.vue"
)
MONITOR_COMPOSABLE = ROOT / "web" / "frontend" / "src" / "composables" / "useMonitorView.ts"
CHAPTERS_LAYOUT = ROOT / "web" / "frontend" / "src" / "views" / "ChaptersLayout.vue"
CHAPTER_SUBNAV = (
    ROOT / "web" / "frontend" / "src" / "components" / "chapter" / "ChapterSubnav.vue"
)
CONFIG_SECTIONS_STACK = (
    ROOT / "web" / "frontend" / "src" / "components" / "config" / "ConfigSectionsStack.vue"
)
PET_WINDOW_INTERACTION = (
    ROOT / "web" / "frontend" / "src" / "composables" / "usePetWindowInteraction.ts"
)
CHAPTER_MAINTENANCE = ROOT / "web" / "frontend" / "src" / "views" / "ChapterMaintenance.vue"
CHAPTER_MAINTENANCE_COMPOSABLE = (
    ROOT / "web" / "frontend" / "src" / "composables" / "useChapterMaintenance.ts"
)

OUTLINE_VIEW = ROOT / "web" / "frontend" / "src" / "views" / "OutlineView.vue"
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
WRITER_CHAPTER_SIDEBAR = (
    ROOT / "web" / "frontend" / "src" / "components" / "writing" / "WritingChapterSidebar.vue"
)
WRITER_RIGHT_SIDEBAR = (
    ROOT / "web" / "frontend" / "src" / "components" / "writing" / "WritingRightSidebar.vue"
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
TROPE_WORKSHOP = ROOT / "web" / "frontend" / "src" / "views" / "TropeWorkshop.vue"
TROPE_COMPONENT_LIBRARY = (
    ROOT / "web" / "frontend" / "src" / "components" / "trope" / "TropeComponentLibrary.vue"
)
TROPE_BLUEPRINT_PANEL = (
    ROOT / "web" / "frontend" / "src" / "components" / "trope" / "TropeBlueprintPanel.vue"
)
TROPE_WORKSHOP_COMPOSABLE = ROOT / "web" / "frontend" / "src" / "composables" / "useTropeWorkshop.ts"
EMPTY_STATE = ROOT / "web" / "frontend" / "src" / "components" / "EmptyStatePanel.vue"
READINESS_CARD = (
    ROOT / "web" / "frontend" / "src" / "components" / "workbench" / "ProjectReadinessCard.vue"
)
COST_PANEL = ROOT / "web" / "frontend" / "src" / "components" / "CostSummaryPanel.vue"
CHAPTER_LIST = ROOT / "web" / "frontend" / "src" / "views" / "ChapterList.vue"
CHAPTER_LIST_TABLE = (
    ROOT / "web" / "frontend" / "src" / "components" / "chapter" / "ChapterListTable.vue"
)
CHAPTER_LIST_COMPOSABLE = ROOT / "web" / "frontend" / "src" / "composables" / "useChapterList.ts"
NOVEL_PROGRESS_HELP = ROOT / "web" / "frontend" / "src" / "components" / "NovelProgressHelp.vue"
BATCH_BANNER = ROOT / "web" / "frontend" / "src" / "components" / "BatchRunStatusBanner.vue"
AGENT_PRODUCTION_LINE = (
    ROOT / "web" / "frontend" / "src" / "components" / "workbench" / "AgentProductionLine.vue"
)
FACTORY_CONTROL_PANEL = (
    ROOT / "web" / "frontend" / "src" / "components" / "workbench" / "FactoryControlPanel.vue"
)
PRODUCTION_PLAN_PANEL = (
    ROOT / "web" / "frontend" / "src" / "components" / "workbench" / "ProductionPlanPanel.vue"
)
FACTORY_PIPELINE_PANEL = (
    ROOT / "web" / "frontend" / "src" / "components" / "workbench" / "FactoryPipelinePanel.vue"
)
REPAIR_COMMAND_PANEL = (
    ROOT / "web" / "frontend" / "src" / "components" / "workbench" / "RepairCommandPanel.vue"
)
LONGFORM_STABILITY_PANEL = (
    ROOT / "web" / "frontend" / "src" / "components" / "workbench" / "LongformStabilityPanel.vue"
)
NATURALNESS_RISK_PANEL = (
    ROOT / "web" / "frontend" / "src" / "components" / "workbench" / "NaturalnessRiskPanel.vue"
)
CHAPTER_DETAIL = ROOT / "web" / "frontend" / "src" / "views" / "ChapterDetail.vue"
CHAPTER_DETAIL_HEADER = (
    ROOT / "web" / "frontend" / "src" / "components" / "chapter" / "ChapterDetailHeader.vue"
)
CHAPTER_DETAIL_COMPOSABLE = ROOT / "web" / "frontend" / "src" / "composables" / "useChapterDetail.ts"
EMBEDDING_CONFIG = ROOT / "web" / "frontend" / "src" / "components" / "EmbeddingConfig.vue"
PIPELINE_RUNTIME = ROOT / "web" / "frontend" / "src" / "components" / "PipelineRuntimeConfig.vue"
SHANSHAN_COPY = ROOT / "web" / "frontend" / "src" / "constants" / "shanshanCopy.ts"
FRONTEND_API = ROOT / "web" / "frontend" / "src" / "api.ts"


def test_writer_supports_chapter_delete_right_sidebar_collapse_and_ai_reload() -> None:
    writer_source = WRITER.read_text(encoding="utf-8")
    chapter_source = WRITER_CHAPTER.read_text(encoding="utf-8")
    ai_write_source = WRITER_AI_WRITE.read_text(encoding="utf-8")

    assert "deleteChapter" in chapter_source
    assert "handleDeleteChapter" in writer_source
    assert "rightSidebarCollapsed" in writer_source
    assert "pollAiWriteResult" in ai_write_source
    assert "await loadChapter(chapterId)" in ai_write_source


def test_writer_save_button_uses_toolbar_style_instead_of_green_block() -> None:
    source = WRITER.read_text(encoding="utf-8")
    assert 'type="success"\n              size="default"\n              icon="DocumentChecked"\n              class="premium-btn btn-save"' not in source
    assert "linear-gradient(135deg, #16a34a, #65a30d)" not in source


def test_writer_toolbar_actions_use_even_grid_distribution() -> None:
    source = WRITER_EDITOR_MAIN.read_text(encoding="utf-8")

    assert "grid-template-columns: repeat(auto-fit, minmax(84px, 1fr));" in source
    assert ".action-buttons .premium-btn" in source
    assert "width: 100%;" in source


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


def test_dashboard_auto_accepts_pending_state_candidates() -> None:
    serial_source = DASHBOARD_SERIAL.read_text(encoding="utf-8")
    serialization_pane = DASHBOARD_SERIALIZATION_PANE.read_text(encoding="utf-8")
    assert "candidate.status === 'pending'" in serial_source
    assert "await approveAllProjectCandidates(pid)" in serial_source
    assert "默认自动通过" in serialization_pane


def test_dashboard_exposes_factory_first_screen_panels() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    assert "FactoryControlPanel" in dashboard
    assert "ProductionPlanPanel" in dashboard
    assert "FactoryPipelinePanel" in dashboard
    assert "LongformStabilityPanel" in dashboard
    assert "NaturalnessRiskPanel" in dashboard
    assert "factory-risk-grid" in dashboard
    assert ':quality="qualitySummary"' in dashboard
    assert "RepairCommandPanel" in dashboard
    assert '@next-step="handleProductionPlanNextStep"' in dashboard
    assert "useFactoryStore" in dashboard
    assert "factory-first-screen" in dashboard
    assert "factory-control-panel" in FACTORY_CONTROL_PANEL.read_text(encoding="utf-8")
    assert "factory-export-check" in FACTORY_CONTROL_PANEL.read_text(encoding="utf-8")
    assert "production-plan-panel" in PRODUCTION_PLAN_PANEL.read_text(encoding="utf-8")
    assert "factory-pipeline-panel" in FACTORY_PIPELINE_PANEL.read_text(encoding="utf-8")
    assert "quality-summary-strip" in FACTORY_PIPELINE_PANEL.read_text(encoding="utf-8")
    assert "longform-stability-panel" in LONGFORM_STABILITY_PANEL.read_text(encoding="utf-8")
    assert "naturalness-risk-panel" in NATURALNESS_RISK_PANEL.read_text(encoding="utf-8")
    assert "repair-command-panel" in REPAIR_COMMAND_PANEL.read_text(encoding="utf-8")


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


def test_library_book_cards_use_spine_without_tick_overlay() -> None:
    source = LIBRARY_BOOK_GRID.read_text(encoding="utf-8")
    assert 'class="book-spine-shadow"' in source
    assert 'class="book-spine"' in source
    assert "aria-hidden=\"true\"" in source
    assert "book-tick" not in source
    assert "✓" not in source.split("book-cover")[0]


def test_project_manager_uses_cached_pipeline_alert_count() -> None:
    source = (ROOT / "web" / "project_manager.py").read_text(encoding="utf-8")
    assert "count_pipeline_alerts_cached" in source


def test_library_cards_show_pending_alert_badge() -> None:
    grid_source = LIBRARY_BOOK_GRID.read_text(encoding="utf-8")
    projects_source = LIBRARY_PROJECTS.read_text(encoding="utf-8")
    assert "pending_alert_count" in grid_source
    assert 'class="pending-badge"' in grid_source
    assert "待处理" in grid_source
    assert "openPendingMaintenance" in projects_source
    assert "expand=alerts" in projects_source


def test_empty_state_panel_used_in_key_views() -> None:
    library = LIBRARY_VIEW.read_text(encoding="utf-8")
    task_log = TASK_LOG.read_text(encoding="utf-8")
    pending = (
        ROOT / "web" / "frontend" / "src" / "components" / "PendingChaptersPanel.vue"
    ).read_text(encoding="utf-8")
    assert "EmptyStatePanel" in library
    assert "EmptyStatePanel" in task_log
    assert "EmptyStatePanel" in pending
    assert "empty-state-panel" in EMPTY_STATE.read_text(encoding="utf-8")


def test_readiness_card_exposes_progress_bar() -> None:
    source = READINESS_CARD.read_text(encoding="utf-8")
    assert "readiness-progress" in source
    assert "progressPercent" in source


def test_chapter_list_exposes_gate_only_rerun() -> None:
    table_source = CHAPTER_LIST_TABLE.read_text(encoding="utf-8")
    composable_source = CHAPTER_LIST_COMPOSABLE.read_text(encoding="utf-8")
    assert "只重跑门禁" in table_source
    assert "rerunGateOnly" in composable_source


def test_monitor_includes_cost_summary_panel() -> None:
    shell_source = MONITOR.read_text(encoding="utf-8")
    tabs_source = MONITOR_TABS.read_text(encoding="utf-8")
    assert "MonitorTabsPane" in shell_source
    assert "CostSummaryPanel" in tabs_source
    assert "cost-api-pane" in tabs_source
    assert "hide-recent-rounds" in tabs_source


def test_monitor_task_logs_splits_rounds_and_task_log() -> None:
    tabs_source = MONITOR_TABS.read_text(encoding="utf-8")
    assert "task-rounds-split" in tabs_source
    assert "AutopilotRoundsPanel" in tabs_source
    assert "TaskLog" in tabs_source
    task_logs_block = tabs_source.split('name="task_logs"', 1)[1].split('name="agent_logs"', 1)[0]
    assert "CostSummaryPanel" not in task_logs_block


def test_pending_panel_has_filter_tabs() -> None:
    source = (
        ROOT / "web" / "frontend" / "src" / "components" / "PendingChaptersPanel.vue"
    ).read_text(encoding="utf-8")
    assert "pending-filter-tabs" in source
    assert "activeFilterId" in source


def test_app_shows_backend_offline_alert() -> None:
    source = APP.read_text(encoding="utf-8")
    assert "backend-offline-alert" in source
    assert "栖墨后台未响应" in source
    assert "HEALTH_FAIL_THRESHOLD" in source


def test_batch_dialog_blocks_submit_when_external_review_active() -> None:
    dialog = (
        ROOT / "web" / "frontend" / "src" / "components" / "NovelBatchRunDialog.vue"
    ).read_text(encoding="utf-8")
    composable = (
        ROOT / "web" / "frontend" / "src" / "composables" / "useNovelBatchRun.ts"
    ).read_text(encoding="utf-8")
    assert "isExternalBlockActive" in composable
    assert "isExternalBlockActive" in dialog


def test_pending_panel_scopes_select_all_to_filter() -> None:
    source = (
        ROOT / "web" / "frontend" / "src" / "components" / "PendingChaptersPanel.vue"
    ).read_text(encoding="utf-8")
    assert "全选当前筛选" in source
    assert "filteredAlerts.value" in source


def test_cost_summary_panel_handles_load_error() -> None:
    source = COST_PANEL.read_text(encoding="utf-8")
    assert "persisted_error" in source
    assert "loadError" in source


def test_chapter_pages_hide_rewrite_actions_without_final_text() -> None:
    list_source = CHAPTER_LIST_TABLE.read_text(encoding="utf-8")
    detail_header_source = CHAPTER_DETAIL_HEADER.read_text(encoding="utf-8")
    detail_composable_source = CHAPTER_DETAIL_COMPOSABLE.read_text(encoding="utf-8")

    assert 'v-if="!row.is_missing"' in list_source
    assert 'class="chapter-edit-btn"' in list_source
    assert ">编辑<" in list_source.replace("\n", "").replace(" ", "")
    assert 'v-if="hasFinalText"' in detail_header_source
    assert "const hasFinalText = computed" in detail_composable_source


def test_embedding_config_stays_collapsed_by_default() -> None:
    source = EMBEDDING_CONFIG.read_text(encoding="utf-8")
    assert "const expanded = ref(false)" in source
    assert "long_form_vector_recommended" in source


def test_api_errors_prefer_backend_detail_over_status_text() -> None:
    api_source = FRONTEND_API.read_text(encoding="utf-8")
    library_source = LIBRARY_PROJECTS.read_text(encoding="utf-8")
    chapter_list_source = CHAPTER_LIST_COMPOSABLE.read_text(encoding="utf-8")
    writer_chapter_source = WRITER_CHAPTER.read_text(encoding="utf-8")

    assert "export const apiErrorMessage" in api_source
    assert "error?.response?.data?.detail" in api_source
    assert "error?.response?.status" in api_source
    assert "Request failed with status code" in api_source
    assert "error.message = message" in api_source
    assert "apiErrorMessage(error" in library_source
    assert "apiErrorMessage(error" in chapter_list_source
    assert "apiErrorMessage(e" in writer_chapter_source


def test_task_log_uses_tasks_store_with_manual_refresh() -> None:
    source = TASK_LOG.read_text(encoding="utf-8")
    assert "Refresh" in source
    assert "refreshing" in source
    assert "useTasksStore" in source
    assert "refreshTaskList" in source
    assert "@click=\"handleRefresh\"" in source
    assert "window.setInterval(refreshTasks, 2000)" not in source


def test_sidebar_brand_uses_single_line_inkrest_lockup() -> None:
    source = APP.read_text(encoding="utf-8")
    assert 'class="brand-lockup"' in source
    assert 'class="brand-cn">栖墨</strong>' in source
    assert 'class="brand-en">INKREST</span>' in source
    assert "<small>智能长篇写作空间</small>" in source


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
    assert "navigate('/chapters/maintenance')" in composable_source
    assert "onNavigate('/chapters/maintenance')" in status_source
    assert "<span>📊 运行监控</span>" not in source


def test_monitor_logs_fill_remaining_viewport_height() -> None:
    monitor_source = MONITOR.read_text(encoding="utf-8")
    task_source = TASK_LOG.read_text(encoding="utf-8")
    log_source = LOG_STREAM.read_text(encoding="utf-8")

    assert "min-height: calc(100vh - 96px);" in monitor_source
    assert "height: calc(100vh - 96px);" in monitor_source
    assert "max-height: 320px" not in task_source
    assert "height: 100%;" in task_source
    assert "max-height: 400px" not in log_source
    assert "height: 100%;" in log_source


def test_settings_page_applies_shared_fold_card_alignment() -> None:
    config_source = CONFIG_VIEW.read_text(encoding="utf-8")
    runtime_source = PIPELINE_RUNTIME.read_text(encoding="utf-8")

    assert ".config-page :deep(.fold-head)" in config_source
    assert ".config-page :deep(.fold-body)" in config_source
    assert ".fold-card {" not in runtime_source


def test_chapter_maintenance_exposes_repair_queue_grouping() -> None:
    maintenance = CHAPTER_MAINTENANCE.read_text(encoding="utf-8")
    composable = CHAPTER_MAINTENANCE_COMPOSABLE.read_text(encoding="utf-8")
    pending = (
        ROOT / "web" / "frontend" / "src" / "components" / "PendingChaptersPanel.vue"
    ).read_text(encoding="utf-8")
    semi = (ROOT / "web" / "frontend" / "src" / "components" / "SemiAutoRepairHint.vue").read_text(
        encoding="utf-8"
    )
    shanshan = SHANSHAN_COPY.read_text(encoding="utf-8")
    assert "useChapterMaintenance" in maintenance
    assert "expand !== 'alerts'" in composable
    assert "lastExpandedQuery" in composable
    assert "expandPendingPanel" in composable
    assert "PendingChaptersPanel" in maintenance
    assert "修章队列" in pending
    assert "展开修章队列" in semi
    assert "SHANSHAN_REPAIR_STEPS_HINT" in shanshan


def test_chapters_layout_exposes_list_and_maintenance_subnav() -> None:
    layout_source = CHAPTERS_LAYOUT.read_text(encoding="utf-8")
    subnav_source = CHAPTER_SUBNAV.read_text(encoding="utf-8")
    list_source = CHAPTER_LIST.read_text(encoding="utf-8")
    maintenance_source = CHAPTER_MAINTENANCE.read_text(encoding="utf-8")

    assert "ChapterSubnav" in layout_source
    assert 'to="/chapters/list"' in subnav_source
    assert 'to="/chapters/maintenance"' in subnav_source
    assert "chapter-subnav__badge" in subnav_source
    assert "复制全书已有正文" not in list_source
    assert ":link-focus=\"true\"" in maintenance_source
    assert "SemiAutoRepairHint" in maintenance_source
    assert "PendingChaptersPanel" in maintenance_source


def test_tasks_store_uses_polling_reference_counts() -> None:
    tasks_source = (ROOT / "web" / "frontend" / "src" / "stores" / "tasks.ts").read_text(
        encoding="utf-8"
    )
    log_stream_source = (
        ROOT / "web" / "frontend" / "src" / "components" / "LogStream.vue"
    ).read_text(encoding="utf-8")

    assert "taskPollConsumers" in tasks_source
    assert "runtimeLogPollConsumers" in tasks_source
    assert "wsAllowReconnect" in tasks_source
    assert "startRuntimeLogPolling" not in log_stream_source


def test_writing_chapter_editor_guards_save_and_load_races() -> None:
    editor_source = (
        ROOT / "web" / "frontend" / "src" / "composables" / "useWritingChapterEditor.ts"
    ).read_text(encoding="utf-8")

    assert "let loadSeq = 0" in editor_source
    assert "loadingEditor.value" in editor_source
    assert "seq !== loadSeq" in editor_source
    assert "escapeHtml" in editor_source


def test_monitor_llm_logs_tab_wires_viewer() -> None:
    tabs_source = MONITOR_TABS.read_text(encoding="utf-8")
    router_source = (ROOT / "web" / "frontend" / "src" / "router.ts").read_text(encoding="utf-8")

    assert 'name="logs"' in tabs_source
    assert "LLMLogViewer" in tabs_source
    assert "费用与接口" in tabs_source
    compact_router = router_source.replace(" ", "").replace("'", '"')
    assert 'redirect:"/monitor?tab=logs"' in compact_router


def test_monitor_page_is_log_center_without_tasks_tab() -> None:
    shell_source = MONITOR.read_text(encoding="utf-8")
    tabs_source = MONITOR_TABS.read_text(encoding="utf-8")
    composable_source = MONITOR_COMPOSABLE.read_text(encoding="utf-8")
    assert ">日志中心<" in shell_source.replace("\n", "").replace(" ", "")
    assert "任务执行监控" not in shell_source
    assert "NovelProgressHelp" not in shell_source
    assert 'name="task_logs"' in tabs_source
    assert "费用与接口" in tabs_source
    assert "router.replace('/chapters/maintenance')" in composable_source
    assert "interface_logs" in composable_source


def test_batch_banner_prioritizes_repair_before_force_resume() -> None:
    source = BATCH_BANNER.read_text(encoding="utf-8")
    assert "先处理待处理章" in source
    assert "仍继续写书" in source
    assert "useNovelBatchRun" in source
    assert "needsRepairBeforeResume" in source
    assert "formatBatchPauseReason" in source


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
    gate = (
        ROOT / "web" / "frontend" / "src" / "components" / "ChapterUnifiedGate.vue"
    ).read_text(encoding="utf-8")
    assert "INTERNAL_GATE_HINT" in source
    assert "EXTERNAL_AUDIT_HINT" in source
    assert "INTERNAL_GATE_HINT" in gate


def test_task_log_and_pet_share_task_step_labels() -> None:
    task_source = TASK_LOG.read_text(encoding="utf-8")
    pet_source = (ROOT / "web" / "frontend" / "src" / "stores" / "pet.ts").read_text(
        encoding="utf-8"
    )
    labels_source = (
        ROOT / "web" / "frontend" / "src" / "utils" / "taskStepLabels.ts"
    ).read_text(encoding="utf-8")
    assert "formatTaskStep" in task_source
    assert "formatTaskStep" in pet_source
    assert "writer: 'AI 写作正文初稿'" in labels_source


def test_llm_log_viewer_fills_remaining_height() -> None:
    source = (
        ROOT / "web" / "frontend" / "src" / "components" / "LLMLogViewer.vue"
    ).read_text(encoding="utf-8")
    assert "log-table-region" in source
    assert 'max-height="520"' not in source


def test_outline_page_places_progress_help_above_queue_status() -> None:
    source = OUTLINE_VIEW.read_text(encoding="utf-8")
    template = source.split("<template>", 1)[1]
    help_idx = template.index("<NovelProgressHelp")
    queue_idx = template.index("<OutlineQueueStatus")
    assert help_idx < queue_idx


def test_progress_help_uses_shared_novel_progress_composable() -> None:
    help_source = NOVEL_PROGRESS_HELP.read_text(encoding="utf-8")
    banner_source = BATCH_BANNER.read_text(encoding="utf-8")
    assert "useNovelProgress" in help_source
    assert "useNovelProgress" in banner_source
    assert "getNovelBatchStatus" not in help_source


def test_shanshan_copy_points_to_chapter_maintenance_not_monitor() -> None:
    source = SHANSHAN_COPY.read_text(encoding="utf-8")
    assert "章节维护" in source
    assert "运行监控" not in source


def test_readme_documents_current_entrypoints() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "python -m pytest" in readme
    assert "python main.py serve" in readme
    assert "electron:pack" in readme
    assert "栖墨.exe" in readme
    assert "python -m unittest tests.test_pipeline" not in readme


def test_batch_run_primary_button_opens_dialog_not_split_menu() -> None:
    source = AGENT_PRODUCTION_LINE.read_text(encoding="utf-8")
    assert "split-button" not in source
    assert "设置章数与选项" not in source
    assert "await openDialog()" in source
    assert "roundProgress" in source
    app_source = APP.read_text(encoding="utf-8")
    assert "NovelBatchRunDialog" in app_source
    assert "NovelBatchRunDialog" not in DASHBOARD.read_text(encoding="utf-8")


def test_longform_vector_warn_surfaces_in_readiness_and_dialog() -> None:
    readiness = (ROOT / "web" / "frontend" / "src" / "utils" / "projectReadiness.ts").read_text(
        encoding="utf-8"
    )
    card = (ROOT / "web" / "frontend" / "src" / "components" / "workbench" / "ProjectReadinessCard.vue").read_text(
        encoding="utf-8"
    )
    dialog = (ROOT / "web" / "frontend" / "src" / "components" / "NovelBatchRunDialog.vue").read_text(
        encoding="utf-8"
    )
    assert "longFormVectorWarn" in readiness
    assert "vector-warn-banner" in card
    assert "长篇向量建议" in dialog


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
    assert "统一门禁摘要" in copy_source
    assert "章节维护" in copy_source
    assert "章节详情" in copy_source
    assert "你现在想先处理哪一件？" in copy_source
    assert "'全书暂停了，怎么续跑？'" in copy_source
    assert "'日常档和逻辑档怎么选？'" in copy_source


def test_writer_shell_delegates_to_subcomponents() -> None:
    source = WRITER.read_text(encoding="utf-8")
    assert "WritingChapterSidebar" in source
    assert "WritingEditorMain" in source
    assert "WritingRightSidebar" in source
    assert "WritingWorkspaceDialogs" in source


def test_writer_chapter_sidebar_supports_collapse_and_delete() -> None:
    source = WRITER_CHAPTER_SIDEBAR.read_text(encoding="utf-8")
    assert "章节目录" in source
    assert "onDeleteChapter" in source
    assert "defineModel<boolean>('collapsed'" in source.replace(" ", "")


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
    assert "OutlineMindmapPane" in source
    assert "OutlineClassicPane" in source
    assert "OutlineDialogs" in source
    assert "OutlineGenesPanel" in source


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
    assert "onDelete" in source


def test_trope_workshop_shell_delegates_to_subcomponents() -> None:
    source = TROPE_WORKSHOP.read_text(encoding="utf-8")
    composable_source = TROPE_WORKSHOP_COMPOSABLE.read_text(encoding="utf-8")
    assert "TropeComponentLibrary" in source
    assert "TropeBlueprintPanel" in source
    assert "useTropeWorkshop" in source
    assert "listComponents" in composable_source
    assert "composePreset" in composable_source
    assert "parsedGuideHtml" in composable_source


def test_trope_component_library_keeps_draggable_cards() -> None:
    source = TROPE_COMPONENT_LIBRARY.read_text(encoding="utf-8")
    assert "defineModel<TropeTab>('activeTab'" in source
    assert 'draggable="true"' in source
    assert "card-add-btn" in source
    assert "onAddToBlueprint" in source


def test_trope_blueprint_panel_keeps_slots_and_preview() -> None:
    source = TROPE_BLUEPRINT_PANEL.read_text(encoding="utf-8")
    assert "blueprint-slots" in source
    assert "markdown-preview" in source
    assert "以此新建作品" in source
    assert "应用到当前作品" in source


def test_config_view_shell_delegates_to_nav_and_sections() -> None:
    shell_source = CONFIG_VIEW.read_text(encoding="utf-8")
    stack_source = CONFIG_SECTIONS_STACK.read_text(encoding="utf-8")
    assert "ConfigPageNav" in shell_source
    assert "ConfigSectionsStack" in shell_source
    assert "useConfigNavigation" in shell_source
    assert "LLMConfig" in stack_source
    assert "EmbeddingConfig" in stack_source


def test_monitor_shell_delegates_to_tabs_pane() -> None:
    shell_source = MONITOR.read_text(encoding="utf-8")
    composable_source = MONITOR_COMPOSABLE.read_text(encoding="utf-8")
    assert "MonitorTabsPane" in shell_source
    assert "useMonitorView" in shell_source
    assert "startRuntimeLogPolling" in composable_source


def test_pet_view_shell_delegates_to_window_interaction() -> None:
    shell_source = (ROOT / "web" / "frontend" / "src" / "views" / "PetView.vue").read_text(
        encoding="utf-8"
    )
    interaction_source = PET_WINDOW_INTERACTION.read_text(encoding="utf-8")
    assert "usePetWindowInteraction" in shell_source
    assert "PetSprite" in shell_source
    assert "togglePetBubble" in interaction_source
    assert "applyEdgeDockIfNeeded" in interaction_source

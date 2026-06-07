# Changelog

## Unreleased

### Refactor

- Dashboard：composable 拆分（workbench / serial / batch / polling）+ 5 个子组件（Workbench / Metrics / Serialization / 两个 Dialog）
- Dashboard 纯函数抽至 `dashboardEngine` / `dashboardChapterGoal` 并补 Vitest
- WritingWorkspace：拆出 8 个 composable（章节编辑 / 版本 / 废稿 / 编辑器辅助 / AI 写作 / 快照 / 平台反馈 + visual settings）
- WritingWorkspace：4 个模板子组件（章节侧栏 / 编辑器主区 / 右侧栏 / 对话框）
- StateView：拆出 settings / chronicle / relation-graph composable + `stateViewFilters` 纯函数与 Vitest
- StateView：2 个模板子组件（剧情设定库 Tab / 时空编年史 Tab）
- LibraryView：拆出 projects / description / cover composable + `libraryFormatters` 纯函数
- LibraryView：2 个模板子组件（书库网格 / 详情与封面对话框）
- OutlineView：拆出 `useOutlineView` / `useOutlineMindmap` composable（加载、表单、卷队列同步、书名选择、类型基因、思维导图连线）
- OutlineView：4 个模板子组件（类型基因面板 / 思维导图 / 传统视图 / 对话框）
- AssetEditor：拆出 `useAssetEditor` composable + `assetEditorConfig` 常量/类型
- AssetEditor：3 个模板子组件（资产列表侧栏 / 编辑面板 / 对话框）
- PetBubbleView：拆出 `usePetBubbleView` composable（Tab 状态、对话发送、诊断折叠、导航、滚动）
- PetBubbleView：`petMarkdown` 纯函数与 Vitest
- PetBubbleView：2 个模板子组件（状态 Tab / 对话 Tab）
- ChapterList：拆出 `useChapterList` composable（加载、筛选、门禁重跑、复制、删除、补齐流水线）
- ChapterList：2 个模板子组件（章节表格 / 补齐对话框）
- PluginManager：拆出 `usePluginManager` composable + `pluginManagerConfig` 常量/类型
- PluginManager：4 个模板子组件（指标卡片 / 筛选栏 / 插件网格 / 对话框）
- TropeWorkshop：拆出 `useTropeWorkshop` composable（元件加载、蓝图选择、compose 预览、应用到作品）
- TropeWorkshop：2 个模板子组件（元件库 Tab / 蓝图工作台与预览）
- ReaderView：拆出 `useReaderView` composable + 3 个模板子组件（工具栏 / 目录抽屉 / 正文阅读区）
- ChapterDetail：拆出 `useChapterDetail` composable + 4 个模板子组件（告警 / 页头 / Tabs / 编辑对话框）
- CreateWizard：拆出 `useCreateWizard` composable + 4 个模板子组件（模式 Tab / 快速 / 解析 / AI 引导）
- ConfigView：拆出 `useConfigNavigation` + `configSections` + 2 个子组件（分区导航 / 设置栈）
- MonitorView：拆出 `useMonitorView` + `MonitorTabsPane`（三 Tab 日志布局）
- PetView：拆出 `usePetWindowInteraction`（拖拽、贴边、气泡切换）
- ChaptersLayout：抽出 `ChapterSubnav` 子组件

### Tests

- Vitest：`libraryFormatters` + `petMarkdown` + `viewSubcomponents` 子组件结构契约
- 契约测试扩展：Writing / State / Outline / Library / AssetEditor / PetBubble / ChapterList / PluginManager / TropeWorkshop / Reader / ChapterDetail / CreateWizard 子组件路径
- E2E：`workspace-state.spec.ts`（写作页侧栏与工具栏、状态库双 Tab）
- E2E：`assets-pet.spec.ts`（项目资产侧栏/面板、山山气泡状态与对话 Tab）
- E2E：`chapters-plugins.spec.ts`（章节列表门禁重跑、插件管理网格）
- E2E：`smoke-routes.spec.ts`（设置 / 日志中心 / 套路工坊 / 书库冒烟）

### Performance (Phase 0–4)

### Backend

- Progress summary 3s TTL cache; pipeline alerts disk cache; batch-status dedupe
- Task progress writes debounced (500ms per task+step)
- Calibration / scale-profile use SQLite chapter index with disk sync fallback
- `progress_snapshot.json` materialized for lightweight project list stats
- `list_projects` uses indexed chapter/word counts instead of full-disk glob
- Incremental `sync_chapters_from_disk` via mtime manifest
- WebSocket `/ws/tasks` pushes task list on change (coalesced ~350ms)

### Frontend

- `pollingGate` + `pollingHub`: skip polls when tab hidden; shared poll timers
- TaskLog reads `tasksStore.taskList`; shallow log/task reactivity
- Monitor lazy tabs; Dashboard adaptive refresh (3s running / 15s idle)
- Element Plus on-demand auto-import
- WS connected时停止 2s 任务 HTTP 轮询，失败才降级

### Tooling / CI

- `npm run build:analyze` — Rollup bundle visualizer (`dist/bundle-stats.html`)
- `scripts/check_frontend_bundle.py` + `benchmarks/frontend_bundle_budget.json`
- `scripts/perf_api_baseline.py` + `benchmarks/api_perf_baseline.json`
- CI: bundle budget + API perf checks after frontend build
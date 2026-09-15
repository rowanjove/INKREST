# Changelog

## [2.1.0] - 2026-09-15

### 🌟 灵感工坊与故事蓝图 (Story Blueprint)
- **灵感编译推演**：从核心母题、冲突机制到三幕情节推演，将碎片化灵感编译为结构化故事蓝图。
- **大纲与场景卡生成**：支持自动生成卷纲计划、章节细纲与场景动作卡片，无缝衔接正文生产流水线。

### ✍️ 人机协同写作引擎 (Human Writing Engine, HWE)
- **深度去 AI 味双重约束**：融合前置提示词文风注入与后置全文文风精修，精准剔除套路化修饰与机械过渡。
- **受保护选区机制**：支持对作者手写正文、经典金句及关键对白进行保护锁定，防止 AI 覆写改动。
- **行内精准润色**：提供段落扩写、精简、润色及定向局部修正闭环，让作者保持最高主导权。

### 🔌 插件平台 2.0 (Plugin Platform & SDK)
- **IPC 进程沙箱与权限体系**：双进程运行隔离，采用声明式能力代理与清单哈希授权，保障系统数据安全。
- **官方 SDK 发布**：发布第一方 `@inkrest/plugin-sdk` 2.0，规范插件生命周期与扩展点注册标准。
- **第一方示范插件**：内置伏笔巡检 (`foreshadow_inspector`) 与剧本杀推理 (`script_murder`) 官方示范扩展。

### 🛡️ 生产中心与质量中心全面升级
- **长篇生产流水线**：全书连写支持场景并行写作、断点续跑、连续失败自动熔断与任务进度持久化。
- **全景质量门禁**：整合情节连续性检查、敏感词合规、剧情冲突拦截与一键定向修章闭环。
- **扩展题材预设**：新增多套高能爽点、叙事机制与热门长篇题材预设模版。

### 📦 资产与文档完善
- **高清界面画廊**：生成并集成 8 大核心模块高分辨率 Retina 截图。
- **双语文档升级**：全面重构中英文 README，强化快速上手、本地离线模型部署指南与架构解读。
- **全套门禁验证**：通过 1,450+ 后端测试、256 项前端测试及 Bundle 体积合规检查。

## [2.0.2] - 2026-08-23

### 隐私与文档

- 将公开文档中的本机绝对路径替换为通用占位符，避免暴露开发环境目录。

## [2.0.1] - 2026-08-23

### 长篇与发布

- 冻结长篇能力基线：区分档位硬上限、项目软目标和单次运行预算；epic 仍为 3000 章，5000 章需使用无限连载。
- 正文/发布目录改为服务端分页与搜索；TXT/Markdown 改为 SQLite 流式导出。
- 新增长篇状态/导出基准命令（默认不调用模型、不写入真实 `projects/`）。

### 变更

- 清理未被运行时、构建或测试引用的参考资料、旧脚本、样板文件和冗余图片资源。
- 将预设生成器归入 `scripts/`，并忽略 PyInstaller 自动生成的根目录 spec 文件。
- GitHub Actions 改用 Node.js 22.12；完整 E2E 工作流只在定时或手动触发，避免与提交门禁重复执行。
- 补齐前端 Node.js 版本约束并重新生成跨平台依赖锁文件。

## [2.0.0] - 2026-07-28

### 新增

- 重构为九个清晰入口：书库、新建作品、项目概览、策划、正文、生产、发布、设置与扩展。
- 新增项目级 SQLite V2 真源、正文修订、任务状态事件、项目快照和发布工作区。
- 新增 TXT、Markdown、DOCX、EPUB 与 PDF 五格式导出。
- 新增项目级去密钥备份、安全重置、插件权限和桌面单实例保护。
- 新增内置示例书、中文项目说明与真实界面截图。

### 变更

- 统一 Vue 3 工作台与 Electron 桌面壳，旧页面入口仅保留路由兼容跳转。
- 页面加载和状态读取不再触发模型调用；生成、重写、审校与批量运行均需显式操作。
- 正文、任务与叙事状态统一以 SQLite 为真源，YAML 与章节文件仅作兼容投影或产物。
- 清理无入口页面、组件、工具与 API 包装，补齐前端生产依赖和完整验证门禁。

### Fixed

- 连写弹窗：禁用遮罩误触关闭、打开后 400ms 内锁定交互；移除外审阻断时自动跳转；连写结束后用事件刷新工作台
- 连写弹窗：修复工作台 `busy` watch 在开弹窗时误触发 `loadWorkbench` 导致弹窗闪退；仅在实际连写结束时刷新
- 连写弹窗：刷新后不再因 readiness 与按钮状态不一致而静默拦截；章节计数与工作台对齐；弹窗全局单例挂载
- 连写：`tasksStore` 轮询 acquire 恢复幂等连接；`submit` 不再重复 acquire；工作台/章节维护页统一托管轮询生命周期
- 写作页：`loadChapter` 请求代际 + 自动保存在 `loadingEditor` 时跳过，避免切章写错内容
- `tasksStore`：任务/运行时日志轮询引用计数 + 有意断开时禁止 WS 自动重连
- `LogStream` 不再在 Tab 卸载时误停 Monitor 日志轮询；`AgentProductionLine` 卸载时释放轮询
- 移除未路由的 `CallLogView` 死代码；契约/E2E 对齐 Monitor「费用与接口」Tab
- LLM 资产同步通知对 `label` 做 HTML 转义；AI 写作轮询在 composable 卸载时停止

## [1.0.0] - 2026-06-07

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
- ChapterMaintenance：拆出 `useChapterMaintenance`（`expand=alerts` 自动展开修章队列）
- CallLogView：抽出 `CallLogPageHead` 页头子组件

### Tests

- Vitest：`libraryFormatters` + `petMarkdown` + `viewSubcomponents` 子组件结构契约
- 契约测试扩展：Writing / State / Outline / Library / AssetEditor / PetBubble / ChapterList / PluginManager / TropeWorkshop / Reader / ChapterDetail / CreateWizard / ChapterMaintenance / CallLogView 子组件路径
- E2E：`workspace-state.spec.ts`（写作页侧栏与工具栏、状态库双 Tab）
- E2E：`assets-pet.spec.ts`（项目资产侧栏/面板、山山气泡状态与对话 Tab）
- E2E：`chapters-plugins.spec.ts`（章节列表门禁重跑、插件管理网格）
- E2E：`smoke-routes.spec.ts`（设置 / 日志中心 / 套路工坊 / 书库 / LLM 日志 Tab 冒烟）
- Bundle budget：`max_total_js_bytes` 调至 1780000（Phase 0–4 拆分后体积基线）

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

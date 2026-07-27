# 栖墨 V2 Phase 2 应用外壳与设计系统 Implementation Plan

**Goal:** 将 1,000 行级 `App.vue` 拆成可维护的应用层，建立全局/项目双层导航、可靠 hydration、统一快照 store、命令面板与基础 UI 规范，为后续五个中心页面提供稳定外壳。

**Architecture:** 新增 `app/`、`entities/`、`shared/` 分层，但不在本阶段机械搬迁全部旧页面。`App.vue` 只装配启动逻辑与 `AppShell`；项目状态由 `ProjectSnapshot` store 统一读取；路由元数据成为导航和访问范围真相源；旧 URL 暂保留。Element Plus 继续承担基础控件，新增轻量封装，不引入与现有设计系统重叠的新 UI 框架。

**Compatibility:** 现有页面和 Electron pet 路由继续工作。旧的 `/workspace`、`/outline`、`/writer`、`/monitor`、`/reader` 等路由保留到对应中心完成替换；本阶段只改变入口层级与应用壳。

**Tech Stack:** Vue 3、Pinia、Vue Router、Element Plus、Vitest、Playwright、TypeScript

---

## Task 1：建立前端 ProjectSnapshot 契约与 store

**Files:**

- Create: `web/frontend/src/entities/project/projectSnapshot.ts`
- Create: `web/frontend/src/entities/project/projectSnapshot.test.ts`
- Create: `web/frontend/src/stores/projectSnapshot.ts`
- Create: `web/frontend/src/stores/projectSnapshot.test.ts`
- Modify: `web/frontend/src/api.ts`

- [x] 定义无 `any` 的快照、任务、阻断、下一步动作 DTO。
- [x] 接入 `GET /api/projects/current/snapshot`。
- [x] store 支持 hydration、刷新去重、错误保留与项目切换失效。
- [x] 单元测试覆盖并发刷新、切书和失败后保留最后有效快照。

## Task 2：修复路由 hydration、范围元数据与滚动

**Files:**

- Create: `web/frontend/src/app/router/routeMeta.ts`
- Create: `web/frontend/src/app/router/navigation.ts`
- Create: `web/frontend/src/app/router/navigation.test.ts`
- Modify: `web/frontend/src/router.ts`
- Modify: `web/frontend/src/stores/project.ts`

- [x] project store 提供幂等 `hydrate()`，明确 `idle/loading/ready/error`。
- [x] 路由守卫先等待 hydration，再判断项目范围，避免深链刷新误跳书库。
- [x] 路由通过 meta 声明 global/project/pet 范围与页面标题。
- [x] 普通切页回到顶部，hash 导航定位目标。
- [x] 测试覆盖深链启动、无项目重定向、全局页放行、滚动行为。

## Task 3：拆分 AppShell 与统一导航

**Files:**

- Create: `web/frontend/src/app/shell/AppShell.vue`
- Create: `web/frontend/src/app/shell/AppSidebar.vue`
- Create: `web/frontend/src/app/shell/AppTopbar.vue`
- Create: `web/frontend/src/app/shell/RuntimeStatusButton.vue`
- Create: `web/frontend/src/app/shell/shell.test.ts`
- Modify: `web/frontend/src/App.vue`

- [x] 无项目时只显示书库、新建作品、设置、扩展。
- [x] 项目内主导航固定为概览、策划、正文、生产、发布。
- [x] 灵感工坊、日志中心、状态库、素材等不再占用顶级导航。
- [x] 显示当前项目、面包屑、全局命令入口和运行状态。
- [x] `App.vue` 只保留 bootstrap/overlay 装配，不再计算业务就绪状态。

## Task 4：命令面板

**Files:**

- Create: `web/frontend/src/app/commands/commandRegistry.ts`
- Create: `web/frontend/src/app/commands/commandRegistry.test.ts`
- Create: `web/frontend/src/app/commands/CommandPalette.vue`
- Create: `web/frontend/src/app/commands/useCommandPalette.ts`

- [x] `Ctrl/Cmd+K` 打开，Esc 关闭，上下键选择，Enter 执行。
- [x] 搜索页面、设置入口、章节、人物和可执行的快照 next actions。
- [x] 搜索结果按类型分组，空结果和加载失败有明确状态。
- [x] 不在命令面板内触发生成；生成类 intent 只导航到确认页面。

## Task 5：诊断抽屉与运行状态

**Files:**

- Create: `web/frontend/src/app/diagnostics/DiagnosticsDrawer.vue`
- Create: `web/frontend/src/app/diagnostics/diagnostics.ts`
- Create: `web/frontend/src/app/diagnostics/diagnostics.test.ts`
- Modify: `web/frontend/src/app/shell/AppShell.vue`

- [ ] 运行状态由 `ProjectSnapshot` 与后端 health 构造，不再发散请求七个接口。
- [ ] 正常状态只显示侧栏底部小指示器；点击后打开抽屉。
- [ ] 抽屉展示阻断、警告、活跃任务、成本和可执行下一步。
- [ ] 内部枚举映射为中文标签，不直接展示 `missing/low/stable`。

## Task 6：共享页面原语与令牌

**Files:**

- Create: `web/frontend/src/shared/ui/PageShell.vue`
- Create: `web/frontend/src/shared/ui/EmptyState.vue`
- Create: `web/frontend/src/shared/ui/ErrorState.vue`
- Create: `web/frontend/src/shared/ui/StatusBadge.vue`
- Create: `web/frontend/src/shared/ui/uiPrimitives.test.ts`
- Modify: `web/frontend/src/styles/tokens.css`
- Modify: `web/frontend/src/styles/global-surfaces.css`

- [ ] 补齐 spacing、layout、focus、motion、z-index 与状态令牌。
- [ ] 页面头、空状态、错误状态和状态徽标使用统一可访问结构。
- [ ] 控件具备可见 focus，尊重 `prefers-reduced-motion`。
- [ ] 共享 UI 不发业务请求。

## Task 7：验证、视觉 QA 与阶段提交

**Files:**

- Modify: `web/frontend/e2e/smoke-routes.spec.ts`
- Create: `web/frontend/e2e/app-shell.spec.ts`
- Modify: `docs/superpowers/plans/2026-07-27-v2-phase-2-app-shell-design-system.md`

- [ ] Vitest、TypeScript 与生产构建通过。
- [ ] Playwright 验证深链、五项项目导航、四项全局导航、命令面板和最小宽度。
- [ ] 使用 Browser 在 1440×900 与 1100×720 检查亮/暗主题、滚动、抽屉和键盘操作。
- [ ] 后端 UI contract 回归通过。
- [ ] 记录 bundle 和实际验证结果并提交。

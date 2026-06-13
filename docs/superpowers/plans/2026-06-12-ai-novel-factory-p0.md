# AI Novel Factory P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first sellable-product loop for the AI novel factory: a production-control first screen, a normalized production plan artifact, and an automatic repair path that gives users a next action instead of a raw failure.

**Architecture:** Reuse the existing Vue/FastAPI architecture and current novel generation services. Add a thin product layer that summarizes existing project readiness, outline, chapter queue, task status, pipeline alerts, quality reports, and repair actions into factory-facing UI blocks. Avoid deep agent rewrites in P0; this plan focuses on orchestration visibility and workflow closure.

**Tech Stack:** Python/FastAPI, SQLite-backed project state, Vue 3, TypeScript, Pinia, Element Plus, existing task WebSocket/polling, existing chapter/gate/export APIs.

---

## Scope

This plan implements P0 from `docs/superpowers/specs/2026-06-12-ai-novel-factory-product-design.md`.

In scope:

- Workbench first screen as an AI factory control surface.
- A normalized “production plan” view assembled from current outline/project metadata/readiness data.
- Factory mode labels and entry points, without changing deep runtime behavior yet.
- Automatic repair as the default next action for blocked chapters when existing repair/gate endpoints can support it.
- Clear manual fallback instructions when automatic repair cannot proceed.
- Frontend tests and backend contract tests for the new product-level workflow.

Out of scope:

- Full account system.
- Cloud/SaaS deployment.
- New third-party platform submission automation.
- A guaranteed bypass of any AI detector.
- Full workstudio permissions.
- Deep rewriting of all generation agents.

## P0 Closeout Notes (2026-06-13)

- Implemented the factory dashboard API, mode profile, operator brief, recommended commands, production-plan next steps, pipeline status, repair summary, quality summary, and export preflight.
- Implemented the workbench first screen with factory control, production plan, production-line status, repair commands, quality summary, and export preflight entry.
- `GET /api/factory/dashboard` is read-only. It must not trigger chapter generation, repair, export, or batch production.
- Real 10-chapter generation smoke testing remains operator-approved only, because project policy forbids auto-triggering generation without explicit user approval.
- P0 verification uses backend contract tests, frontend unit tests, frontend build, workspace UI contract tests, and local browser visual QA.

## File Structure

Expected files to modify or create:

- `web/routes/factory.py`
  - New backend route module for product-level factory summaries.
  - Aggregates existing project, outline, chapter, task, alert, and export status into UI-friendly payloads.

- `web/server.py` or existing route registration module
  - Register the new factory routes.

- `web/models.py` or `web/routes/factory.py`
  - Define Pydantic response models for factory dashboard, production plan, and repair recommendations.

- `tests/api/test_factory_dashboard.py`
  - Backend tests for factory summary, missing plan states, blocked chapter repair recommendations, and no active project behavior.

- `web/frontend/src/api.ts`
  - Add typed client calls for factory summary and repair recommendations.

- `web/frontend/src/types/factory.ts`
  - Add frontend-facing TypeScript types for factory dashboard data.

- `web/frontend/src/views/Dashboard.vue`
  - Reframe the existing workbench first screen around AI factory control.

- `web/frontend/src/components/workbench/FactoryControlPanel.vue`
  - New top-level factory status and action panel.

- `web/frontend/src/components/workbench/ProductionPlanPanel.vue`
  - New normalized production plan panel.

- `web/frontend/src/components/workbench/FactoryPipelinePanel.vue`
  - Reuse or wrap the existing production-line animation with clearer factory labels.

- `web/frontend/src/components/workbench/RepairCommandPanel.vue`
  - Show blocked chapters, automatic repair actions, and manual fallback instructions.

- `web/frontend/src/stores/factory.ts`
  - Pinia store for factory summary data and refresh actions.

- `web/frontend/src/utils/factoryStatus.ts`
  - Pure functions for dashboard labels, risk level mapping, mode labels, and action availability.

- `web/frontend/src/utils/factoryStatus.test.ts`
  - Vitest tests for pure status mapping.

- `tests/test_workspace_ui_contract.py`
  - Extend contract tests to assert the presence of factory control, production plan, and repair command components.

## Data Contracts

### Factory Dashboard Response

Backend endpoint:

```text
GET /api/factory/dashboard
```

Response shape:

```json
{
  "project": {
    "id": "abc123",
    "name": "示例项目",
    "scale": "medium",
    "mode": "newbie_auto"
  },
  "production_plan": {
    "status": "ready",
    "title": "书名",
    "selling_points": ["爽点1", "爽点2"],
    "target_chapters": 120,
    "planned_chapters": 10,
    "readiness": {
      "ok": 7,
      "total": 9,
      "missing": ["角色卡", "卷队列"]
    }
  },
  "factory_status": {
    "state": "blocked",
    "current_stage": "repair",
    "completed_chapters": 8,
    "target_chapters": 120,
    "running_tasks": 0,
    "risk_level": "high"
  },
  "pipeline": [
    {"id": "planning", "label": "策划", "state": "done"},
    {"id": "writing", "label": "写作", "state": "idle"},
    {"id": "audit", "label": "审校", "state": "warning"},
    {"id": "repair", "label": "修复", "state": "blocked"}
  ],
  "repair": {
    "blocked_count": 2,
    "items": [
      {
        "chapter_id": "008",
        "title": "第八章",
        "reason": "AI 味过重",
        "recommended_action": "auto_repair",
        "manual_hint": "重点改写第 3-5 段的抽象抒情和重复句式。"
      }
    ]
  },
  "quality_summary": {
    "status": "blocked",
    "total_reports": 8,
    "passed": 7,
    "failed": 1,
    "ai_flavor_risks": 1,
    "latest_issue": {
      "chapter_id": "008",
      "blocked_by": ["ai_flavor"],
      "ai_flavor_risk": "high"
    }
  },
  "export_check": {
    "status": "blocked",
    "can_export": false,
    "blockers": ["存在 1 章质检未通过"],
    "warnings": ["发现 1 章 AI 味风险"],
    "route": "/workspace",
    "primary_action": "处理阻断"
  },
  "exports": {
    "txt_available": true,
    "epub_available": true,
    "pdf_available": false
  }
}
```

Allowed dashboard states:

- `empty`: no active project or no usable outline.
- `planning`: project exists but production plan is incomplete.
- `ready`: plan is ready and no task is running.
- `running`: generation or repair task is active.
- `blocked`: one or more chapters require repair.
- `complete`: target range is complete.

Allowed mode labels:

- `newbie_auto`: 新手全自动
- `author_copilot`: 作者协作
- `platform_review`: 平台过审
- `longform_stable`: 长篇稳定
- `studio`: 工作室生产

## Task 1: Backend Factory Dashboard Contract

**Files:**

- Create: `web/routes/factory.py`
- Modify: `web/server.py`
- Test: `tests/api/test_factory_dashboard.py`

- [ ] **Step 1: Write backend tests for no active project and ready project**

Create `tests/api/test_factory_dashboard.py` with tests that use the existing FastAPI test client pattern in `tests/api/`.

Test cases:

- `GET /api/factory/dashboard` returns `state: "empty"` when no active project is available.
- A fixture project with outline/readiness data returns `production_plan.status` as either `planning` or `ready`.
- The response always contains `project`, `production_plan`, `factory_status`, `pipeline`, `repair`, and `exports` keys.

Run:

```powershell
python -m pytest tests/api/test_factory_dashboard.py -q --tb=short
```

Expected:

```text
FAILED ... /api/factory/dashboard ... 404
```

- [ ] **Step 2: Add the factory route module**

Create `web/routes/factory.py`.

Implementation notes:

- Reuse existing project/session helpers from `web/deps.py` or the route pattern already used by `web/routes/projects.py` and `web/routes/outlines.py`.
- Start with conservative aggregation:
  - If no active project, return `empty`.
  - If a project exists but no outline or queue readiness, return `planning`.
  - If pipeline alerts or blocked chapters exist, return `blocked`.
  - If running task exists, return `running`.
  - Otherwise return `ready`.
- Do not trigger generation or repair from this endpoint.

- [ ] **Step 3: Register `/api/factory/dashboard`**

Modify the existing FastAPI app registration so the route is mounted with the other `/api/*` routes.

Run:

```powershell
python -m pytest tests/api/test_factory_dashboard.py -q --tb=short
```

Expected:

```text
... passed
```

- [ ] **Step 4: Run related backend contract tests**

Run:

```powershell
python -m pytest tests/api/test_api_chapters.py tests/test_workspace_ui_contract.py tests/api/test_factory_dashboard.py -q --tb=short
```

Expected:

```text
... passed
```

Commit:

```powershell
git add web/routes/factory.py web/server.py tests/api/test_factory_dashboard.py
git commit -m "feat: add factory dashboard summary api"
```

## Task 2: Frontend Factory Types, API, and Status Utilities

**Files:**

- Create: `web/frontend/src/types/factory.ts`
- Create: `web/frontend/src/utils/factoryStatus.ts`
- Create: `web/frontend/src/utils/factoryStatus.test.ts`
- Modify: `web/frontend/src/api.ts`

- [ ] **Step 1: Add TypeScript types**

Create `web/frontend/src/types/factory.ts` with interfaces matching the backend response:

- `FactoryDashboard`
- `FactoryProject`
- `ProductionPlanSummary`
- `FactoryStatusSummary`
- `FactoryPipelineStep`
- `FactoryRepairSummary`
- `FactoryRepairItem`
- `FactoryExportSummary`

Use string unions for known states and modes.

- [ ] **Step 2: Add API client method**

Modify `web/frontend/src/api.ts` to export:

```ts
export async function getFactoryDashboard(): Promise<FactoryDashboard> {
  const { data } = await api.get<FactoryDashboard>('/api/factory/dashboard')
  return data
}
```

Import `FactoryDashboard` from the new type file.

- [ ] **Step 3: Write Vitest coverage for status labels**

Create `web/frontend/src/utils/factoryStatus.test.ts` covering:

- `newbie_auto` maps to `新手全自动`.
- `blocked` maps to a primary action of `自动修复`.
- `planning` maps to a primary action of `生成生产计划`.
- High risk maps to a danger display tone.

Run:

```powershell
cd web/frontend
npm run test:unit -- factoryStatus
```

Expected:

```text
FAIL ... Cannot find module './factoryStatus'
```

- [ ] **Step 4: Implement status utilities**

Create `web/frontend/src/utils/factoryStatus.ts` with pure functions:

- `formatFactoryMode(mode)`
- `formatFactoryState(state)`
- `getFactoryPrimaryAction(dashboard)`
- `getFactoryTone(riskLevel)`

Run:

```powershell
cd web/frontend
npm run test:unit -- factoryStatus
```

Expected:

```text
... passed
```

Commit:

```powershell
git add web/frontend/src/types/factory.ts web/frontend/src/utils/factoryStatus.ts web/frontend/src/utils/factoryStatus.test.ts web/frontend/src/api.ts
git commit -m "feat: add factory dashboard frontend contract"
```

## Task 3: Factory Dashboard Store

**Files:**

- Create: `web/frontend/src/stores/factory.ts`
- Modify: `web/frontend/src/views/Dashboard.vue`

- [ ] **Step 1: Add Pinia store**

Create `web/frontend/src/stores/factory.ts`.

Store state:

- `dashboard`
- `loading`
- `error`
- `lastLoadedAt`

Actions:

- `loadDashboard()`
- `refreshDashboard()`

Behavior:

- `loadDashboard()` calls `getFactoryDashboard()`.
- Errors produce a human-readable message.
- The store should not start generation or repair.

- [ ] **Step 2: Wire store into Dashboard without changing layout**

Modify `web/frontend/src/views/Dashboard.vue` only enough to load the factory dashboard on mount and refresh after known task changes if the view already has such hooks.

Run:

```powershell
cd web/frontend
npm run test:unit
npm run build
```

Expected:

```text
... passed
✓ built
```

Commit:

```powershell
git add web/frontend/src/stores/factory.ts web/frontend/src/views/Dashboard.vue
git commit -m "feat: load factory dashboard on workbench"
```

## Task 4: Factory Control Panel UI

**Files:**

- Create: `web/frontend/src/components/workbench/FactoryControlPanel.vue`
- Modify: `web/frontend/src/views/Dashboard.vue`
- Test: `tests/test_workspace_ui_contract.py`

- [ ] **Step 1: Extend UI contract test**

Modify `tests/test_workspace_ui_contract.py` to assert that `Dashboard.vue` references `FactoryControlPanel`.

Run:

```powershell
python -m pytest tests/test_workspace_ui_contract.py -q
```

Expected:

```text
FAILED ... FactoryControlPanel
```

- [ ] **Step 2: Create FactoryControlPanel**

Create `FactoryControlPanel.vue`.

UI content:

- Project title and mode label.
- Production state.
- Chapter progress.
- Risk tone.
- Primary action button text from `getFactoryPrimaryAction`.

Primary action behavior:

- `planning`: navigate to create/outline or existing plan generation entry.
- `ready`: open existing batch run dialog.
- `running`: navigate to task monitor.
- `blocked`: focus repair panel or navigate to chapter maintenance.
- `empty`: navigate to create.

Use existing Element Plus button and badge patterns.

- [ ] **Step 3: Place panel at top of Dashboard**

Modify `Dashboard.vue` to show `FactoryControlPanel` as the first major block.

Run:

```powershell
cd web/frontend
npm run build
cd ../..
python -m pytest tests/test_workspace_ui_contract.py -q
```

Expected:

```text
... passed
```

Commit:

```powershell
git add web/frontend/src/components/workbench/FactoryControlPanel.vue web/frontend/src/views/Dashboard.vue tests/test_workspace_ui_contract.py
git commit -m "feat: add factory control panel"
```

## Task 5: Production Plan Panel

**Files:**

- Create: `web/frontend/src/components/workbench/ProductionPlanPanel.vue`
- Modify: `web/frontend/src/views/Dashboard.vue`
- Test: `tests/test_workspace_ui_contract.py`

- [ ] **Step 1: Extend contract test for production plan**

Assert `Dashboard.vue` references `ProductionPlanPanel`.

Run:

```powershell
python -m pytest tests/test_workspace_ui_contract.py -q
```

Expected:

```text
FAILED ... ProductionPlanPanel
```

- [ ] **Step 2: Create ProductionPlanPanel**

Display:

- Plan status.
- Book title.
- Selling points.
- Target chapters.
- Planned chapters.
- Readiness progress.
- Missing items with action links where available.

Empty/planning state:

- Show a clear action to generate or complete the production plan.

- [ ] **Step 3: Add panel below factory control**

Run:

```powershell
cd web/frontend
npm run build
cd ../..
python -m pytest tests/test_workspace_ui_contract.py -q
```

Expected:

```text
... passed
```

Commit:

```powershell
git add web/frontend/src/components/workbench/ProductionPlanPanel.vue web/frontend/src/views/Dashboard.vue tests/test_workspace_ui_contract.py
git commit -m "feat: show production plan on workbench"
```

## Task 6: Pipeline and Repair Panels

**Files:**

- Create: `web/frontend/src/components/workbench/FactoryPipelinePanel.vue`
- Create: `web/frontend/src/components/workbench/RepairCommandPanel.vue`
- Modify: `web/frontend/src/views/Dashboard.vue`
- Test: `tests/test_workspace_ui_contract.py`

- [ ] **Step 1: Extend contract tests**

Assert `Dashboard.vue` references:

- `FactoryPipelinePanel`
- `RepairCommandPanel`

Run:

```powershell
python -m pytest tests/test_workspace_ui_contract.py -q
```

Expected:

```text
FAILED ... FactoryPipelinePanel
```

- [ ] **Step 2: Create FactoryPipelinePanel**

Display pipeline steps from the dashboard response:

- 策划
- 写作
- 润色
- 审校
- 修复
- 入库/导出

State display:

- done
- active
- warning
- blocked
- idle

Reuse the visual language of the existing production line component where possible.

- [ ] **Step 3: Create RepairCommandPanel**

Display:

- Blocked count.
- Each blocked chapter.
- Reason.
- Recommended action.
- Manual hint.
- Action buttons:
  - 自动修复
  - 去改稿
  - 只重跑门禁

If an action endpoint is not available yet, disable the button and show the manual hint.

- [ ] **Step 4: Add both panels to Dashboard**

Run:

```powershell
cd web/frontend
npm run build
cd ../..
python -m pytest tests/test_workspace_ui_contract.py -q
```

Expected:

```text
... passed
```

Commit:

```powershell
git add web/frontend/src/components/workbench/FactoryPipelinePanel.vue web/frontend/src/components/workbench/RepairCommandPanel.vue web/frontend/src/views/Dashboard.vue tests/test_workspace_ui_contract.py
git commit -m "feat: add factory pipeline and repair panels"
```

## Task 7: Repair Action Wiring

**Files:**

- Modify: `web/routes/factory.py`
- Modify: `web/frontend/src/api.ts`
- Modify: `web/frontend/src/components/workbench/RepairCommandPanel.vue`
- Test: `tests/api/test_factory_dashboard.py`

- [ ] **Step 1: Add backend test for repair recommendations**

Extend `tests/api/test_factory_dashboard.py`:

- When pipeline alerts include a blocked chapter, `repair.items[0].recommended_action` is `auto_repair` or `manual_edit`.
- Each repair item includes `manual_hint`.

Run:

```powershell
python -m pytest tests/api/test_factory_dashboard.py -q --tb=short
```

Expected:

```text
FAILED ... manual_hint
```

- [ ] **Step 2: Implement repair recommendation mapping**

In `web/routes/factory.py`, map known alert/failure kinds:

- AI flavor/style issue -> `auto_repair`
- gate blocked with existing gate rerun path -> `rerun_gate`
- missing input/config -> `manual_edit`
- unknown failure -> `manual_edit`

Generate concise manual hints from available alert text. If no detail exists, use:

```text
请打开章节详情，优先检查门禁报告中标红的问题段落，修改后只重跑门禁。
```

- [ ] **Step 3: Wire frontend repair buttons**

In `RepairCommandPanel.vue`:

- `auto_repair`: call existing rewrite/repair endpoint if present in `api.ts`; otherwise route to chapter detail with repair context.
- `rerun_gate`: call existing gate rerun endpoint if present; otherwise route to chapter detail.
- `manual_edit`: route to writing workspace or chapter detail.

Do not invent destructive actions.

- [ ] **Step 4: Run backend and frontend checks**

Run:

```powershell
python -m pytest tests/api/test_factory_dashboard.py tests/api/test_api_chapters.py -q --tb=short
cd web/frontend
npm run test:unit
npm run build
```

Expected:

```text
... passed
✓ built
```

Commit:

```powershell
git add web/routes/factory.py web/frontend/src/api.ts web/frontend/src/components/workbench/RepairCommandPanel.vue tests/api/test_factory_dashboard.py
git commit -m "feat: surface factory repair actions"
```

## Task 8: Visual QA and Regression Verification

**Files:**

- No code changes expected unless QA finds issues.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
python -m pytest tests/ --ignore=tests/smoke -q --tb=short
```

Expected:

```text
... passed
```

- [ ] **Step 2: Run frontend checks**

Run:

```powershell
cd web/frontend
npm run test:unit
npm run build
```

Expected:

```text
... passed
✓ built
```

- [ ] **Step 3: Start local app for browser QA**

Run the normal local backend/frontend flow used by this project. If a dev server port is already occupied, use the next available port.

Verify:

- Workbench first screen shows factory control first.
- Production plan panel is visible.
- Pipeline panel is visible.
- Repair panel is visible when blocked chapters exist.
- Empty project state directs user to create a project.
- Text does not overlap at desktop and narrow widths.

- [ ] **Step 4: Update docs if behavior changed**

If visible workflow names or routes changed, update:

- `PROJECT.md`
- `PROJECT_STRUCTURE.md`
- `docs/IMPROVEMENT-ROADMAP-2026Q2.md`

Commit:

```powershell
git add PROJECT.md PROJECT_STRUCTURE.md docs/IMPROVEMENT-ROADMAP-2026Q2.md
git commit -m "docs: document factory dashboard workflow"
```

Only commit docs that actually changed.

## Final Verification

Before claiming completion:

```powershell
python -m pytest tests/ --ignore=tests/smoke -q --tb=short
cd web/frontend
npm run test:unit
npm run build
cd ../..
python -m pytest tests/test_workspace_ui_contract.py -q
```

Expected:

```text
All selected tests pass, and frontend build completes successfully.
```

## Execution Recommendation

Use subagent-driven development for implementation:

- Task 1: backend contract.
- Tasks 2-3: frontend data layer.
- Tasks 4-6: UI panels.
- Task 7: repair wiring.
- Task 8: verification and polish.

Review after each task because the work touches the product’s first impression.

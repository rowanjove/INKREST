# Monitor And Settings Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the Pro preset into old model libraries, shorten Shanshan monitoring copy, expand monitoring logs to the viewport, and align settings cards.

**Architecture:** Extend model-library load reconciliation without overwriting existing entries. Use flex and grid sizing in the monitor view so both log panels consume remaining height. Consolidate settings fold-card geometry around the global styles.

**Tech Stack:** Python, Vue 3, TypeScript, CSS, pytest, Vite

---

### Task 1: Add failing contracts

**Files:**
- Modify: `tests/api/test_api_config.py`
- Modify: `tests/test_workspace_ui_contract.py`

- [ ] Add a model-library test proving missing Pro is restored without overwriting Flash edits.
- [ ] Add UI contract tests for short Shanshan copy, flexible log height, and aligned settings cards.
- [ ] Run focused tests and confirm failures.

### Task 2: Reconcile built-in models

**Files:**
- Modify: `web/model_library.py`

- [ ] Reconcile every missing built-in model during load.
- [ ] Preserve stored entries exactly when their IDs already exist.
- [ ] Run the model-library test and confirm it passes.

### Task 3: Polish monitoring and settings UI

**Files:**
- Modify: `web/frontend/src/views/PetBubbleView.vue`
- Modify: `web/frontend/src/views/MonitorView.vue`
- Modify: `web/frontend/src/components/TaskLog.vue`
- Modify: `web/frontend/src/components/LogStream.vue`
- Modify: `web/frontend/src/views/ConfigView.vue`
- Modify: `web/frontend/src/components/PipelineRuntimeConfig.vue`

- [ ] Replace the Shanshan compact navigation label with `监控`.
- [ ] Make both monitor log panels fill remaining viewport height.
- [ ] Remove conflicting runtime fold-card geometry and add settings-page alignment rules.
- [ ] Run UI contracts and frontend build.

### Task 4: Verify

**Files:**
- Verify only

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q novel_agent web`.
- [ ] Run `npm run build` from `web/frontend`.


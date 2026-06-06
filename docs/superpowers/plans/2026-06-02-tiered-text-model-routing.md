# Tiered Text Model Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add daily and reasoning text-model tiers with role inheritance, independent overrides, and backward compatibility.

**Architecture:** Resolve tier inheritance in `novel_agent.pipeline` before building the existing LLM registry. Keep `default_model_id` as a daily-tier compatibility alias. Update the settings UI and all legacy readers to prefer `daily_model_id`.

**Tech Stack:** Python, FastAPI, Vue 3, TypeScript, Element Plus, pytest

---

### Task 1: Runtime tier resolution

**Files:**
- Modify: `tests/test_pipeline.py`
- Modify: `novel_agent/pipeline.py`

- [ ] Add a failing test proving `writer` resolves to daily and `chief_editor` resolves to reasoning.
- [ ] Run `python -m pytest tests/test_pipeline.py -q` and confirm the new test fails.
- [ ] Add default role tiers and expand tier inheritance before calling `create_llm_registry`.
- [ ] Run `python -m pytest tests/test_pipeline.py -q` and confirm it passes.

### Task 2: Configuration compatibility

**Files:**
- Modify: `tests/test_api.py`
- Modify: `web/helpers.py`
- Modify: `web/model_library.py`
- Modify: `web/routes/assistant.py`
- Modify: `config/pipeline.yaml`

- [ ] Add failing tests for seeded tier defaults and deleting referenced tier models.
- [ ] Run the focused pytest tests and confirm they fail.
- [ ] Seed daily and reasoning defaults, clear tier references on delete, and let the assistant inherit daily.
- [ ] Run the focused pytest tests and confirm they pass.

### Task 3: Frontend tier settings

**Files:**
- Modify: `web/frontend/src/components/LLMConfig.vue`
- Modify: `web/frontend/src/components/ModelLibrary.vue`
- Modify: `web/frontend/src/components/PetAssistantConfig.vue`
- Modify: `web/frontend/src/App.vue`
- Modify: `web/frontend/src/views/Dashboard.vue`
- Modify: `web/frontend/src/views/CreateWizard.vue`
- Modify: `tests/test_workspace_ui_contract.py`

- [ ] Add a failing UI contract test for the daily and reasoning selectors.
- [ ] Run `python -m pytest tests/test_workspace_ui_contract.py -q` and confirm it fails.
- [ ] Implement two selectors, inheritance labels, and daily-tier fallbacks in legacy readers.
- [ ] Run the UI contract tests and frontend build.

### Task 4: Verification

**Files:**
- Verify only

- [ ] Run `python -m pytest -q`.
- [ ] Run `npm run build` from `web/frontend`.
- [ ] Review the resulting configuration contract and report the verification evidence.


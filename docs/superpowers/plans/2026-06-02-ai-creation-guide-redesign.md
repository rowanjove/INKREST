# AI Creation Guide Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a six-step AI project bootstrap with an optional four-step deep-planning layer and normalize the resulting project outline.

**Architecture:** Replace the legacy five-step chat handler with a ten-step blueprint state machine. Keep the current HTTP endpoints, then update the Vue guide to render six base progress steps, a reusable finalization panel, and an optional deep-planning phase.

**Tech Stack:** Python, FastAPI, unittest/pytest, Vue 3, TypeScript, Element Plus, Vite

---

### Task 1: Blueprint State Machine

**Files:**
- Modify: `web/novel_chat.py`
- Create: `tests/test_novel_chat.py`

- [ ] Write failing tests for reader-promise extraction, serial-engine extraction, base finalization, deep-planning entry, and deep-planning completion.
- [ ] Run `python -m pytest tests/test_novel_chat.py -q` and verify the new expectations fail against the legacy five-step handler.
- [ ] Replace the legacy handler with explicit handlers for steps 1-10 and a normalized finalization helper.
- [ ] Run `python -m pytest tests/test_novel_chat.py -q` and verify the state-machine tests pass.

### Task 2: Frontend Guide Flow

**Files:**
- Modify: `web/frontend/src/components/AiChatGuide.vue`
- Modify: `web/frontend/src/views/CreateWizard.vue`

- [ ] Render six base-step labels and four deep-step labels.
- [ ] Add a reusable finalization panel with card editing, scale selection, preset composition, immediate creation, and deep-planning entry.
- [ ] Map the emitted context into a normalized project outline containing reader promise, protagonist engine, conflict stage, serial engine, and optional deep-planning fields.
- [ ] Run `npm run build` from `web/frontend`.

### Task 3: Regression Verification

**Files:**
- Verify: `tests/test_novel_chat.py`
- Verify: `tests/test_api.py`

- [ ] Run `python -m pytest tests/test_novel_chat.py tests/test_api.py -q`.
- [ ] Run `npm run build` from `web/frontend`.
- [ ] Confirm the resulting flow removes the legacy card/scale wrapper mismatch and keeps direct project creation working.


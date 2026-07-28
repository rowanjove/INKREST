# Shanshan Pet Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the V0.1/V0.2 Shanshan desktop pet assistant as an enabled-by-default, user-toggleable Electron companion with task-state awareness.

**Architecture:** Electron owns `PetWindow`, `BubbleWindow`, persisted pet settings, and IPC. Vue renders `/pet` and `/pet-bubble`, reads a copied Shanshan asset pack, and maps backend/task state into pet states. FastAPI exposes a lightweight `/api/assistant/context` summary for bubble content without LLM calls.

**Tech Stack:** Electron 42, Vue 3, Pinia, Vue Router, TypeScript, FastAPI, pytest, vue-tsc.

---

### Task 1: Asset Pack

**Files:**
- Create: `web/frontend/src/assets/pet/shanshan/**`
- Create: `web/frontend/src/assets/pet/shanshan/pet.json`

- [ ] Copy generated assets from `D:\path\to\novel-agent\山山` into `web/frontend/src/assets/pet/shanshan`.
- [ ] Add `pet.json` declaring `idle`, `working`, `success`, and `error` animation files plus static fallback files.
- [ ] Verify files exist and WebP/PNG dimensions match the generated outputs.

### Task 2: Assistant Context API

**Files:**
- Create: `web/routes/assistant.py`
- Modify: `web/app.py`
- Modify: `web/server.py`
- Test: `tests/test_assistant_context.py`

- [ ] Write pytest tests for `/api/assistant/context` when no active project is available and when task manager returns tasks.
- [ ] Run those tests and confirm they fail because the route does not exist.
- [ ] Implement a lightweight FastAPI router returning `backend_health`, `active_project`, `running_tasks`, `failed_tasks`, and `recent_logs`.
- [ ] Include the router in `web/app.py` and re-export it in `web/server.py`.
- [ ] Run the assistant context tests and existing API tests.

### Task 3: Electron Pet Settings and Windows

**Files:**
- Create: `web/frontend/electron/pet-settings.ts`
- Create: `web/frontend/electron/windows/pet-window.ts`
- Create: `web/frontend/electron/windows/bubble-window.ts`
- Create: `web/frontend/electron/ipc/pet-ipc.ts`
- Modify: `web/frontend/electron/main.ts`
- Modify: `web/frontend/electron/preload.ts`
- Modify: `web/frontend/src/electron.d.ts`

- [ ] Add settings read/write helpers with defaults, damaged-file backup, and workArea clamping.
- [ ] Add pet and bubble window factories that load `/pet` and `/pet-bubble` in dev/prod.
- [ ] Register IPC handlers for settings, show/hide, bubble toggle, main-window focus/navigation, and relative window movement.
- [ ] Wire pet creation after main window/tray startup when settings say enabled and show-on-startup.
- [ ] Expose IPC methods through preload and TypeScript declarations.
- [ ] Run `npm run build:electron`.

### Task 4: Vue Pet Runtime

**Files:**
- Create: `web/frontend/src/stores/pet.ts`
- Create: `web/frontend/src/components/pet/PetSprite.vue`
- Create: `web/frontend/src/components/pet/PetStatusCard.vue`
- Create: `web/frontend/src/views/PetView.vue`
- Create: `web/frontend/src/views/PetBubbleView.vue`
- Modify: `web/frontend/src/router.ts`
- Modify: `web/frontend/src/api.ts`

- [ ] Add assistant context API client.
- [ ] Add `/pet` and `/pet-bubble` routes that bypass the active-project guard.
- [ ] Add `usePetStore` with settings, context polling, and state mapping.
- [ ] Build `PetSprite` with WebP animation and PNG fallback.
- [ ] Build `PetView` for click, double-click, drag threshold, and right-click menu delegation.
- [ ] Build `PetBubbleView` with project/task/error summary and navigation buttons.
- [ ] Run `npm run build`.

### Task 5: Settings Entry and Final Verification

**Files:**
- Modify: `web/frontend/src/views/ConfigView.vue`
- Verify: `web/frontend/src/assets/pet/shanshan/**`

- [ ] Add a small “桌宠助手” settings section with enable, show-on-startup, always-on-top, and size controls.
- [ ] Confirm setting changes persist via Electron IPC when running in Electron and degrade gracefully in browser/dev.
- [ ] Run backend tests for assistant context.
- [ ] Run frontend and Electron builds.
- [ ] Manually inspect `/pet` and `/pet-bubble` in dev browser for nonblank rendering.

## Plan Self-Review

- Spec coverage: V0.1 window shell, V0.2 state context, settings, asset pack, and future-plugin resource shape are covered.
- Scope control: LLM chat, repair actions, Live2D/Spine, and external plugin loading are excluded.
- Type consistency: IPC names use `pet:*`; pet states are `idle`, `working`, `success`, `error`, `offline`, and `dragging`.

# Hardening And Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the reviewed security boundaries, restore project isolation, improve desktop startup reliability, and remove known compatibility debt.

**Architecture:** Preserve local desktop behavior while making risky capabilities explicit. Imported projects remain data-only, remote serving requires an explicit opt-in and token, project settings stop mutating sibling projects, cover downloads pass through URL and size validation, and Electron chooses an available loopback port.

**Tech Stack:** Python, FastAPI, pytest, Vue, Vite, Electron, TypeScript.

---

### Task 1: Regression coverage

**Files:**
- Modify: `tests/test_security_regressions.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_plugin_manager.py`

- [ ] Add tests for ZIP script rejection, project config isolation, plugin trust defaults, cover URL validation, image format persistence, and HTTPX proxy argument compatibility.
- [ ] Run focused tests and confirm the new tests fail for the expected missing behavior.

### Task 2: Backend security boundaries

**Files:**
- Modify: `web/routes/projects.py`
- Modify: `novel_agent/plugins/manager.py`
- Create: `web/security.py`
- Modify: `web/app.py`
- Modify: `main.py`
- Modify: `web/routes/config.py`

- [ ] Reject executable project archive members.
- [ ] Require explicit state before loading local plugins.
- [ ] Add unsafe-request token middleware and remote serve opt-in.
- [ ] Lock local embedding dependency versions and verify downloaded model hashes when configured.

### Task 3: Data and cover correctness

**Files:**
- Modify: `web/routes/config.py`
- Modify: `web/routes/covers.py`
- Modify: `web/model_library.py`

- [ ] Keep ordinary config updates scoped to the active project.
- [ ] Add an explicit global-default update endpoint.
- [ ] Validate generated cover URLs, limit downloads, preserve real image type, and use HTTPX `proxy=`.

### Task 4: Desktop and tooling reliability

**Files:**
- Modify: `web/frontend/electron/main.ts`
- Modify: `web/frontend/vite.config.ts`
- Create: `pytest.ini`
- Modify: `web/models.py`
- Modify: `requirements.txt`

- [ ] Use a dynamic loopback port in packaged Electron mode.
- [ ] Split vendor bundles.
- [ ] Configure pytest import path and asyncio fixture scope.
- [ ] Remove remaining Pydantic namespace warnings.
- [ ] Keep HTTPX compatible with the implementation.

### Task 5: Verification

- [ ] Run focused regression tests.
- [ ] Run `pytest -q`.
- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q novel_agent web main.py cli.py`.
- [ ] Run `npm run build`.
- [ ] Run `npm run build:electron`.
- [ ] Run `npm audit --omit=dev --json`.

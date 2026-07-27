# Current Worktree Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the current uncommitted worktree by aligning task recovery semantics, removing duplicate audit code, syncing docs/UI with behavior, and preserving the passing test baseline.

**Architecture:** Keep the current local-first FastAPI + SQLite + Vue/Electron architecture. Do not start a broad rewrite; harden the risky boundaries first: task lifecycle, audit phase ownership, state-source docs, and task UI. Each task should leave the project in a passing, independently reviewable state.

**Tech Stack:** Python, FastAPI, SQLite, pytest, Vue 3, Pinia, Element Plus, Vitest, Vite.

---

## Current Baseline

- Backend main suite: `python -m pytest tests/ --ignore=tests/smoke -q --tb=short` -> `741 passed, 5 skipped`.
- Frontend unit suite: `cd web/frontend && npm run test:unit` -> `142 passed`.
- Frontend build: `cd web/frontend && npm run build` -> passed, with third-party Rolldown pure-annotation warnings.
- Important uncommitted files include task lifecycle changes, vector-store split, YAML mirror policy changes, frontend task/config UI changes, and new docs.

## Files And Responsibilities

- `web/tasks.py`: task submission, in-memory execution handles, pending queue polling, abort/failure handling.
- `novel_agent/state/history_repository.py`: SQLite task lifecycle persistence and transition events.
- `novel_agent/state/sqlite_schema.py`: task table schema and migrations.
- `web/frontend/src/stores/tasks.ts`: frontend task list/progress interpretation.
- `web/frontend/src/components/TaskLog.vue`: human-readable task lifecycle display.
- `novel_agent/phases/audit.py`: audit phase orchestration; currently contains duplicate method definitions.
- `novel_agent/phases/audit_rewrite.py`: extracted audit rewrite mixin; should own sync rewrite helpers.
- `docs/TASK-STATE-MACHINE.md`: task lifecycle contract.
- `docs/STATE-SOURCES.md`: authoritative state-source contract.
- `docs/ERROR-BOUNDARY-AUDIT.md`: structured failure boundary roadmap.
- `tests/api/test_api_tasks.py`, `tests/test_state_candidates.py`: task lifecycle tests.
- `web/frontend/src/stores/tasks.processList.test.ts`, `tests/test_workspace_ui_contract.py`: task UI/contract tests.

---

### Task 1: Freeze And Inventory The Worktree

**Files:**
- Read: all modified/untracked files from `git status --short`
- Modify: none

- [ ] **Step 1: Capture the current file inventory**

Run:

```powershell
git status --short
git diff --stat
git diff --name-status
```

Expected: confirms the same broad change groups: task lifecycle, audit/generation refactor, vector split, YAML mirror, config/model UI, docs, and tests.

- [ ] **Step 2: Identify accidental scratch files**

Run:

```powershell
git status --short | Select-String "^\?\?"
```

Expected: review whether `split_vector_store.py` and older advisory plan drafts are intentional. Do not delete anything without explicit user approval.

- [ ] **Step 3: Run the known baseline**

Run:

```powershell
python -m pytest tests/ --ignore=tests/smoke -q --tb=short
cd web/frontend
npm run test:unit
npm run build
```

Expected: backend and frontend remain green before deeper edits.

---

### Task 2: Decide And Encode Task Recovery Policy

**Files:**
- Modify: `web/tasks.py`
- Modify: `novel_agent/state/history_repository.py`
- Modify: `novel_agent/state/sqlite_schema.py`
- Test: `tests/api/test_api_tasks.py`
- Test: `tests/test_state_candidates.py`

- [ ] **Step 1: Write tests for explicit recovery policy**

Add focused tests that pin these rules:

```python
def test_startup_requeues_running_with_reason(self):
    store.save_task("task-1", "001", "goal", False, "pending")
    store.update_task_status("task-1", "running", status_reason="worker_started")
    store.clean_interrupted_tasks(stale_after_seconds=600)
    task = store.get_task("task-1")
    self.assertEqual(task["status"], "pending")
    self.assertIn(task["status_reason"], {"process_interrupted", "stale_heartbeat", "startup_cleanup"})
    self.assertEqual(task["resumable_from"], "unknown")
```

Also add a manager-level test that pending non-single-chapter tasks are never auto-resumed.

- [ ] **Step 2: Run the new tests and verify the current behavior**

Run:

```powershell
python -m pytest tests/api/test_api_tasks.py tests/test_state_candidates.py -q --tb=short
```

Expected: tests either pass with current behavior or expose the exact gap before implementation.

- [ ] **Step 3: Replace prefix-only task classification with a helper**

In `web/tasks.py`, introduce one small helper near the pending loop:

```python
def _is_auto_resumable_single_chapter_task(task: Dict[str, Any]) -> bool:
    goal = str(task.get("goal") or "")
    chapter_id = task.get("chapter_id")
    if not chapter_id:
        return False
    blocked_prefixes = ("batch:", "gate_only:", "Novel:", "Arc batch:")
    return not goal.startswith(blocked_prefixes)
```

Use this helper inside `_run_pending_tasks_loop()` instead of inline prefix checks.

- [ ] **Step 4: Add a durable claim design, but implement minimally**

If staying minimal this cycle, add schema columns without full distributed queue semantics:

```sql
alter table tasks add column task_type text;
alter table tasks add column attempt_count integer default 0;
```

Backfill `task_type` during `save_task()` from caller-provided type in a later task. If avoiding schema expansion now, document that this remains the next migration.

- [ ] **Step 5: Verify**

Run:

```powershell
python -m pytest tests/api/test_api_tasks.py tests/test_state_candidates.py -q --tb=short
python -m pytest tests/ --ignore=tests/smoke -q --tb=short
```

Expected: task tests and full backend suite pass.

---

### Task 3: Make Abort And Failure Payloads Consistent

**Files:**
- Modify: `web/tasks.py`
- Modify: `web/task_failures.py` if needed
- Test: `tests/api/test_api_tasks.py`
- Test: `tests/test_error_codes.py`

- [ ] **Step 1: Add tests for abort metadata**

Add assertions that aborting a pending/running task records:

```python
self.assertEqual(task["status"], "failed")
self.assertEqual(task["status_reason"], "user_abort")
self.assertEqual(task["resumable_from"], task.get("current_step") or "unknown")
```

- [ ] **Step 2: Update `abort_task()`**

Change the direct status update to include metadata:

```python
self.store.update_task_status(
    task_id,
    "failed",
    None,
    "Task aborted by user",
    status_reason="user_abort",
    resumable_from=task_data.get("current_step") or "unknown",
)
```

- [ ] **Step 3: Route batch exceptions through structured failure payloads**

In `_run_batch()`, replace direct `str(exc)` failed writes with `_mark_task_failed(batch_id, exc)`.

- [ ] **Step 4: Verify**

Run:

```powershell
python -m pytest tests/api/test_api_tasks.py tests/test_error_codes.py -q --tb=short
```

Expected: abort and batch failures produce consistent task records.

---

### Task 4: Remove Duplicate AuditPhase Methods

**Files:**
- Modify: `novel_agent/phases/audit.py`
- Test: `tests/test_smart_rewrite.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Confirm duplicate definitions**

Run:

```powershell
rg -n "def _run_continuity_and_summary|def _run_wordcount|def _run_audit_and_extraction|def _run_rewrite_loop" novel_agent/phases/audit.py
```

Expected: duplicate sync definitions are visible before cleanup.

- [ ] **Step 2: Delete the shadowed duplicate block**

Keep one implementation each for:

```python
_run_continuity_and_summary
_run_wordcount
_run_audit_and_extraction
```

If `_run_rewrite_loop`, `_handle_plan_rewrite`, `_handle_paragraph_rewrite`, or `_rewrite_iteration` are duplicated between `audit.py` and `audit_rewrite.py`, prefer keeping the mixin implementation in `audit_rewrite.py`.

- [ ] **Step 3: Verify no duplicate definitions remain**

Run:

```powershell
rg -n "def _run_continuity_and_summary|def _run_wordcount|def _run_audit_and_extraction|def _run_rewrite_loop" novel_agent/phases/audit.py
```

Expected: one definition per method in `audit.py`; rewrite-loop ownership is clear.

- [ ] **Step 4: Run audit/generation tests**

Run:

```powershell
python -m pytest tests/test_smart_rewrite.py tests/test_pipeline.py tests/test_orchestrator.py -q --tb=short
```

Expected: tests pass.

---

### Task 5: Align State And Task Documentation With Reality

**Files:**
- Modify: `docs/TASK-STATE-MACHINE.md`
- Modify: `docs/STATE-SOURCES.md`
- Modify: `docs/ERROR-BOUNDARY-AUDIT.md`

- [ ] **Step 1: Update task recovery docs**

Replace the stale startup recovery section with this policy:

```markdown
On startup, rows left in `running` are requeued to `pending` with `status_reason`
set to `startup_cleanup`, `process_interrupted`, or `stale_heartbeat`.
The current background queue may auto-resume standard single-chapter tasks only.
Batch, gate-only, novel, and arc tasks are not auto-resumed.
```

- [ ] **Step 2: Update YAML mirror docs**

Make `docs/STATE-SOURCES.md` match `resolve_yaml_mirror_mode()`:

```markdown
If `runtime.yaml_mirror_mode` is set, it wins.
If legacy `runtime.yaml_mirror_enabled` exists, `true` maps to `write` and `false` maps to `off`.
If neither exists, the implicit mode is `read_only`.
```

- [ ] **Step 3: Update error boundary roadmap**

Mark abort/batch failure handling as part of the task boundary cleanup and keep config route classification as the next route-level item.

- [ ] **Step 4: Verify docs reference real names**

Run:

```powershell
rg -n "startup_cleanup|process_interrupted|stale_heartbeat|yaml_mirror_mode|read_only|user_abort" docs
```

Expected: docs use the same terms as code and tests.

---

### Task 6: Surface Recovery Metadata In The Frontend

**Files:**
- Modify: `web/frontend/src/stores/tasks.ts`
- Modify: `web/frontend/src/components/TaskLog.vue`
- Test: `web/frontend/src/stores/tasks.processList.test.ts`
- Test: `tests/test_workspace_ui_contract.py`

- [ ] **Step 1: Add frontend store tests for pending single-chapter tasks**

Add a case where a pending single-chapter task with `status_reason: "process_interrupted"` keeps the UI aware of active/recoverable work.

```ts
store.processTasksListForTest([
  { task_id: 't1', chapter_id: '001', status: 'pending', goal: '继续写' },
])
expect(store.taskList[0].status).toBe('pending')
```

- [ ] **Step 2: Show recovery detail in `TaskLog.vue`**

Add a small formatter:

```ts
const recoveryMessage = (task: any) => {
  if (!task.status_reason && !task.resumable_from) return ''
  const reason = task.status_reason ? `原因：${task.status_reason}` : ''
  const from = task.resumable_from ? `恢复点：${task.resumable_from}` : ''
  return [reason, from].filter(Boolean).join(' · ')
}
```

Render it below the progress message when present.

- [ ] **Step 3: Verify**

Run:

```powershell
cd web/frontend
npm run test:unit -- src/stores/tasks.processList.test.ts
cd ../..
python -m pytest tests/test_workspace_ui_contract.py -q --tb=short
```

Expected: frontend task metadata is covered without needing browser interaction.

---

### Task 7: Clean Up Temporary Plan And Scratch Artifacts

**Files:**
- Review: `docs/superpowers/plans/2026-06-16-tech-advisory-roadmap.md`
- Review: `docs/superpowers/plans/2026-06-16-current-worktree-advisory-v2.md`
- Review: `split_vector_store.py`

- [ ] **Step 1: Ask user before deleting anything**

Do not delete untracked files silently. Present this list:

```text
docs/superpowers/plans/2026-06-16-tech-advisory-roadmap.md
docs/superpowers/plans/2026-06-16-current-worktree-advisory-v2.md
split_vector_store.py
```

- [ ] **Step 2: If approved, remove only confirmed scratch files**

Use PowerShell native deletion only after approval:

```powershell
Remove-Item -LiteralPath "confirmed-file-path"
```

- [ ] **Step 3: Verify no accidental source deletion**

Run:

```powershell
git status --short
```

Expected: source files and intended docs remain.

---

### Task 8: Final Verification And Commit Slicing

**Files:**
- No source files unless tests expose a regression.

- [ ] **Step 1: Run full backend verification**

Run:

```powershell
python -m pytest tests/ --ignore=tests/smoke -q --tb=short
```

Expected: pass.

- [ ] **Step 2: Run full frontend verification**

Run:

```powershell
cd web/frontend
npm run test:unit
npm run build
```

Expected: pass; third-party Rolldown annotation warning may remain.

- [ ] **Step 3: Slice commits by risk boundary**

Recommended commit groups:

```text
1. task lifecycle recovery and failure metadata
2. audit phase duplicate cleanup
3. docs alignment
4. frontend task metadata display
5. vector/config/UI refactor files already in current worktree, if reviewed
```

- [ ] **Step 4: Re-check worktree**

Run:

```powershell
git status --short
```

Expected: only intentional modified/untracked files remain.

---

## Execution Notes

- Do not trigger novel generation commands during this plan.
- Preserve unrelated user edits.
- Prefer small commits after each task passes.
- If any task makes the full backend suite fail, stop and fix that task before continuing.
- Keep older advisory files as historical notes only; this plan is the active execution guide.

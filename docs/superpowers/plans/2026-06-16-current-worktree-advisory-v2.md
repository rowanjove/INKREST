# Current Worktree Technical Advisory Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` before implementing any item below. This plan is based on the current uncommitted worktree, not the older 2026-06-15 advisory plan.

**Goal:** Reassess the project after the latest reliability/refactor batch and turn the current code state into a safe next-step guide.

**Architecture:** The project has moved beyond “add task metadata” into an active local queue/resume architecture. The next work must validate that new behavior, not re-propose it.

**Tech Stack:** Python/FastAPI, SQLite, Vue 3/TypeScript, Electron, pytest, Vitest, local task registry, SQLite vector store, Factory runtime policy.

---

## What Changed Since the Older Plan

The older advisory treated task recovery, state-source docs, error payloads, and frontend helper extraction as mostly pending work. The current worktree already contains much of that work:

- `web/tasks.py` now creates a pending-task polling loop and attempts to resume persisted `pending` single-chapter tasks.
- `novel_agent/state/history_repository.py` now records `last_heartbeat`, `status_reason`, `resumable_from`, and `task_status_events`.
- Startup cleanup now appears to move interrupted `running` tasks back to `pending`, not terminal `failed`.
- `novel_agent/state/vector_store.py` has been split, with SQLite/HNSW/Chroma implementation moved into `novel_agent/state/sqlite_vector_store.py`.
- Legacy literal history search moved into `novel_agent/state/history_repository_legacy.py`.
- Agent construction moved toward `novel_agent/services/agent_factory.py`.
- LLM cost persistence moved toward `novel_agent/services/cost_tracker.py`.
- Chapter artifact summary/status is now exposed in API models.
- Frontend model/embedding/error logic has been extracted into utility modules and tests.

## Layer 1: Current Diagnosis

### Top 3 Problems Now

| Priority | Problem | Why it matters now | Fix difficulty |
|----------|---------|--------------------|----------------|
| P0 | Auto-resume semantics are now the highest-risk change. | The system no longer only explains interrupted work; it can requeue/resume persisted tasks. If this is wrong, users can get duplicate chapters, unsafe reruns, or tasks that restart without clear consent. | Medium-high |
| P0 | Refactor integration risk is now larger than missing abstractions. | Vector store, legacy search, agent factory, cost tracker, and artifact status are being split out. The risk is import cycles, behavior drift, and tests still exercising old paths. | Medium |
| P1 | Documentation/contracts are behind the new behavior. | `TASK-STATE-MACHINE.md` still describes conservative failed/interrupted semantics, while code is moving `running -> pending`. UI and tests must match the real product decision. | Low-medium |

### Symptoms vs Root Causes

| Symptom | Root cause |
|---------|------------|
| A task may restart after process restart instead of staying failed. | Cleanup logic has changed from terminal interruption to requeue semantics, but the state machine doc and UX language have not caught up. |
| Batch/novel/arc tasks are skipped by pending loop while single chapter resumes. | The local queue supports only a subset of task kinds; task type is inferred from `goal` string prefixes rather than a durable task type column. |
| Vector code is smaller in the old file but still complex. | Implementation was moved to `sqlite_vector_store.py`, not simplified yet; the new boundary needs import and behavior tests. |
| Current plan says “do X” even though code already does it. | Planning was anchored to 2026-06-15 docs instead of the live diff. |

### Three-Month Debt if Not Corrected

- Silent or partial auto-resume becomes a product trust issue: users will not know whether a chapter was newly generated, resumed, or duplicated.
- Task type inference via strings becomes brittle as more task kinds appear.
- The vector-store split can preserve a 700+ line complexity island under a new filename, making future Chroma/HNSW fixes harder.
- Docs and tests will drift from actual behavior; future agents will keep re-planning already-completed work.

## Layer 2: Immediate Improvement Plan

### Highest ROI Next Steps

| Order | Item | Change | Estimate | Verification |
|-------|------|--------|----------|--------------|
| 1 | Decide auto-resume policy explicitly | Choose one: interrupted tasks become `failed` and require user action, or become `pending` and resume automatically. Current code chooses partial auto-resume for single chapters. Document that as product behavior or revert it. | 1-2h | `docs/TASK-STATE-MACHINE.md` matches `clean_interrupted_tasks()` and `TaskManager._run_pending_tasks_loop()` |
| 2 | Add durable task type | Stop inferring batch/gate/novel/arc from `goal` string prefixes. Add or derive a `task_type` field for persisted tasks, even if old rows fall back to prefix parsing. | 4-8h | API/task tests cover single, batch, gate-only, novel, arc behavior after restart |
| 3 | Verify pending-loop safety | Ensure one process cannot launch duplicates, chapter locks are cleared reliably, and completed/failed rows are never resumed. | 4-8h | Targeted pytest for restart/resume and duplicate prevention |
| 4 | Prove vector split did not change behavior | Test importing `VectorStore`, `SQLiteEmbeddingVectorStore`, `create_vector_store`, delete-by-chapter, chapter-window search, and HNSW fallback. | 3-6h | `python -m pytest tests/test_fallback_vector_store.py tests/test_state_candidates.py -q` plus import smoke |
| 5 | Align docs and UI wording | Update task monitor/readiness copy around `pending`, `process_interrupted`, `stale_heartbeat`, and `resumable_from`. | 2-4h | Frontend unit/build plus task API payload snapshot |
| 6 | Remove stale advisory ambiguity | Treat `2026-06-16-tech-advisory-roadmap.md` as superseded by this v2, or delete it before committing. | 5m | Only one advisory plan is referenced in follow-up work |

### Can Be Done Alongside Features

- Frontend helper extractions around model library, embedding readiness, and error formatting.
- Chapter artifact summary/status propagation to UI.
- Cost tracker display and log polish.
- Agent factory cleanup, if no behavior changes are bundled in.

### Needs Dedicated Focus

- Auto-resume policy and task type persistence.
- Restart/duplicate prevention tests.
- Vector-store split import/behavior validation.
- Updating state-machine docs to match the chosen semantics.

## Layer 3: Medium-Term Direction

### Where 10x Scale Breaks First Now

1. Local task queue semantics: the new pending loop is the first real queue. It needs durable task type, locking/claiming semantics, and clear retry rules before scaling.
2. Vector backend complexity: SQLite, HNSW disk cache, Chroma, stub, local ONNX, and cloud embeddings are all inside one implementation class.
3. Task observability: auto-resume without a visible audit trail will confuse users at long-form scale.
4. Refactor boundary drift: service extraction helps, but only if old files stop owning behavior.

### Recommended Evolution Path

#### Phase A: Queue Contract, 1 Week

- Add durable task type.
- Define claim/resume rules.
- Add restart tests.
- Make UI tell the user when a task was resumed automatically.

#### Phase B: Refactor Verification, 1 Week

- Confirm vector-store split behavior with focused tests.
- Confirm agent factory creates plugin overrides exactly as before.
- Confirm cost tracker clears/accumulates logs correctly across failed and successful chapters.

#### Phase C: State/Artifact Contract, 1 Week

- Keep using `chapter_artifact_status` as shared truth.
- Ensure `artifact_summary` is consumed by list/detail/dashboard paths consistently.
- Update `STATE-SOURCES.md` only after code behavior is verified.

#### Phase D: Queue Backend Boundary, Later

- Extract `TaskBackend` only after local queue behavior is stable.
- Keep SQLite/local execution as default.
- Reserve a future backend for cloud/multi-process, but do not introduce it now.

## Corrected Working Plan

### Milestone 1: Make Current Worktree Truthful

- [ ] Mark the older `2026-06-16-tech-advisory-roadmap.md` as superseded or remove it before commit.
- [ ] Update `docs/TASK-STATE-MACHINE.md` to match actual `running -> pending` behavior, or revert code to `running -> failed`.
- [ ] Run targeted task tests and record the current behavior.
- [ ] Add a test that proves whether interrupted single-chapter tasks auto-resume.

### Milestone 2: Harden the Local Queue

- [ ] Add or derive durable task type.
- [ ] Replace goal-prefix task kind checks in `_run_pending_tasks_loop()`.
- [ ] Add duplicate prevention tests for same chapter/task id.
- [ ] Ensure `_running_chapters` is always cleaned after resume failure.

### Milestone 3: Verify Refactor Boundaries

- [ ] Add import smoke for `novel_agent.state.vector_store`.
- [ ] Test `delete_chapter_vectors()` against normalized and legacy chapter ids.
- [ ] Test agent factory plugin override path.
- [ ] Test cost tracker token accumulator across success/failure boundaries.

### Milestone 4: Frontend and Contract Finish

- [ ] Ensure task UI displays `status_reason`, `resumable_from`, and auto-resume state.
- [ ] Keep `embeddingReadiness` and `modelLibraryForm` covered by Vitest.
- [ ] Keep backend error payload fields aligned with `errorCodes.ts`.

## Bottom Line

The project has advanced past the previous advisory. The next serious risk is no longer “we need a task state machine”; it is “we now have a partial local queue, and its recovery semantics must be made explicit, tested, and visible.”

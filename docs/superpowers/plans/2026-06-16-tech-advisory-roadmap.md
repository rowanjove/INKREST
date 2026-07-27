# Technical Advisory Roadmap Implementation Plan

> **Superseded:** This draft was based too heavily on the older 2026-06-15 advisory framing. Use `docs/superpowers/plans/2026-06-16-current-worktree-advisory-v2.md` for the current uncommitted worktree.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` when converting any workstream below into code tasks. This advisory plan is a decision guide; split selected items into implementation checklists before editing.

**Goal:** Move the project from a feature-rich local novel generator to a reliable long-running writing system with trustworthy state, recoverable tasks, stable contracts, and manageable UI/backend complexity.

**Architecture:** Keep the current local-first architecture: Python/FastAPI backend, Vue 3 + Electron frontend, SQLite as the primary local database, workspace artifacts for generated chapter files, and YAML only as compatibility/export surface. Avoid a large rewrite; harden the boundaries that already exist.

**Tech Stack:** Python, FastAPI, SQLite, Vue 3, TypeScript, Electron, pytest, Vitest, Playwright/E2E, project-level task registry, Factory runtime policy.

---

## Evidence Snapshot

- Current worktree is heavily modified. The reliability batch touches task lifecycle, state storage, vector store split, artifact status, config/error contracts, frontend tasks/config UI, and tests. Treat it as in-progress until verification is green and the branch is made reviewable.
- Relevant docs now exist: `docs/TASK-STATE-MACHINE.md`, `docs/STATE-SOURCES.md`, `docs/ERROR-BOUNDARY-AUDIT.md`, and `docs/FACTORY-MODE-RUNTIME.md`.
- Excluding generated `dist*` and `node_modules`, current source scale is approximately:
  - `web`: 328 files / 55.6k lines
  - `novel_agent`: 148 files / 20.3k lines
  - `tests`: 113 files / 13.4k lines
- Largest active complexity hotspots include:
  - Backend: `web/tasks.py`, `novel_agent/state/history_repository.py`, `novel_agent/state/sqlite_vector_store.py`, `novel_agent/phases/audit.py`, `web/routes/projects.py`, `web/routes/config.py`, `web/routes/assistant.py`
  - Frontend: `ModelLibrary.vue`, `App.vue`, `StateChronicleTab.vue`, `EmbeddingConfig.vue`, `PendingChaptersPanel.vue`
- Broad `except Exception`, compatibility fallbacks, legacy root behavior, and YAML mirror paths are still common. Some are intentional best-effort behavior, but user-facing endpoints need stronger classification.

## Layer 1: Current Diagnosis

### Top 3 Problems, Ordered by Impact x Fix Difficulty

| Priority | Problem | Impact | Fix difficulty | Why this order |
|----------|---------|--------|----------------|----------------|
| P0 | Long-running task reliability is still the product's trust bottleneck. | Affects continue, batch generation, gate-only reruns, Electron disconnects, process restart, and user confidence. | Medium. The state machine and SQLite task fields now exist, but need end-to-end verification and UI affordances. | If users cannot trust long runs, every advanced writing feature feels unsafe. |
| P0 | State and chapter facts still have several sources that can drift. | Affects chapter list, detail page, repair queue, export, continuity state, readiness, and resume decisions. | Medium-high. The source matrix and artifact classifier exist, but every route must obey them. | Generated fiction compounds mistakes; a stale state today becomes wrong continuity later. |
| P1 | Contract and error boundaries lag behind feature growth. | Affects config/model setup, task monitor, Electron packaging, frontend type assumptions, and support/debugging. | Medium. Many pieces exist, but broad catches and oversized modules still hide intent. | New features will keep amplifying regression risk unless contracts become boring and explicit. |

### Symptoms vs Root Causes

| Symptom | Root cause |
|---------|------------|
| Tasks appear stuck, interrupted, duplicated, or hard to resume. | Execution handles live in memory while truth lives in SQLite; recovery semantics are improving but not yet proven by kill/restart scenarios. |
| Chapter list/detail/readiness can disagree. | SQLite chapter index, workspace artifacts, reports, checkpoints, and YAML mirrors historically carried overlapping facts. |
| Errors show as generic failure text in some paths. | Business logic, fallback behavior, and exception classification are mixed inside routes/tasks instead of going through one error boundary. |
| Adding UI fields to config/model pages feels risky. | Large components contain fetching, validation, derived state, display state, and error presentation together. |
| Compatibility code keeps reappearing. | Legacy root mode, YAML mirror, old APIs, and fallback model/config behavior lack clear retirement gates. |

### Three-Month Technical Debt Forecast

- Long-run reliability debt becomes support debt: users will hesitate to run 20-100 chapter flows if restart/abort/retry semantics are unclear.
- State drift becomes content corruption: continuity, foreshadowing, character state, and chapter repair queues will disagree in ways that are hard to reconstruct.
- Compatibility layers become permanent product behavior: YAML mirror and legacy paths will block cleanup unless defaults, export flows, and deprecation windows are explicit.
- Frontend velocity drops: `ModelLibrary.vue`, `EmbeddingConfig.vue`, `StateChronicleTab.vue`, and `App.vue` will turn small UX changes into page-wide regression work.
- Cost and observability gaps grow: audit/rewrite/vector recall are the costly links; without budget, failure, and retry observability, long-form use becomes opaque.

## Layer 2: Near-Term Improvement Plan

### Immediate Roadmap, Smallest Input for Largest Return

| Order | Item | What to change | How to change | Estimate | Verification | Work style |
|-------|------|----------------|---------------|----------|--------------|------------|
| 1 | Freeze a green reliability baseline | Make the current hardening batch reviewable before adding more features. | Run targeted backend/frontend tests, fix regressions, remove accidental generated-file noise, then split commits by task/state/error/frontend. | 3-6h | `python -m pytest tests/test_batch_retry_queue.py tests/api/test_api_tasks.py tests/test_checkpoint_rollback.py -q`; `cd web/frontend && npm run test:unit && npm run build` | Stop and do deliberately |
| 2 | Prove task restart semantics | Validate that SQLite task rows describe interrupted work clearly. | Kill backend during a mock batch; restart; confirm `status_reason`, `last_heartbeat`, `resumable_from`, and UI message. Add/adjust automated test if a gap appears. | 4-8h | Manual kill/restart script plus task API test; no silent auto-resume without explicit action | Stop and do deliberately |
| 3 | Enforce chapter artifact contract | Make list/detail/readiness/repair consume the same artifact classifier. | Audit routes for hand-rolled `has_final`, `gate_status`, checkpoint, report, or workspace checks; route them through `chapter_artifact_status` or index sync. | 6-10h | `python -m pytest tests/test_chapter_artifact_status.py tests/test_chapter_index_metadata.py tests/test_workspace_ui_contract.py -q` | Can be done alongside chapter features |
| 4 | Finish user-facing error classification | Convert config/model/task/chapter request failures into structured error payloads. | Use the existing `novel_agent/errors` and frontend `errorCodes.ts`; leave best-effort assistant context assembly defensive, but classify action endpoints. | 6-12h | `python -m pytest tests/test_error_codes.py tests/api/test_api_config.py tests/api/test_api_tasks.py -q`; UI displays code/hint/action | Can be batched by route |
| 5 | Reduce large UI component risk | Extract pure helpers/composables from the biggest pages without visual redesign. | One page at a time: model form transform, embedding readiness/fix steps, state chronicle filtering/grouping, pending task display state. | 8-16h | `npm run test:unit && npm run build`; Browser/Electron smoke for touched pages | Can be done while touching those pages |
| 6 | Make YAML mirror policy user-visible | Keep compatibility, but stop treating YAML as silent co-primary state. | Surface mirror mode/read-only/export wording in readiness/settings; add drift count where useful. | 4-8h | `python -m pytest tests/test_yaml_mirror.py tests/api/test_api_novel_readiness.py -q` | Small dedicated pass |
| 7 | Add a weekly long-run confidence check | Prevent reliability regressions from returning. | Create or document a repeatable mock long-run: multi-chapter, process restart, failed model config, gate rerun, export. | 3-5h | One command or checklist with expected outcomes; not default PR gate if too slow | Maintenance habit |

### Can Be Done While Building New Features

- Route new chapter/readiness/export code through the artifact classifier.
- Add error contract tests whenever adding or changing an API endpoint.
- Extract pure frontend helpers when touching existing large views.
- Add `schema_version` or explicit response fields when changing config/model payloads.
- Update `STATE-SOURCES.md` when introducing a new artifact or cache.

### Must Be Handled as Dedicated Work

- Making the current hardening batch green and reviewable.
- Kill/restart task recovery validation.
- YAML mirror default/UX decision, because it affects user expectations and legacy compatibility.
- Any change to task terminal states, retry semantics, or implicit resume behavior.

## Layer 3: Medium/Long-Term Evolution

### Where 10x Scale Breaks First

1. Task execution breaks first. A local in-memory execution layer plus SQLite rows can support one desktop user, but 10x chapters/projects/tasks requires strict queue and recovery semantics.
2. State/query consistency breaks next. Chapter artifacts, SQLite index rows, vector recall, reports, and YAML compatibility need one contract per fact or they will drift.
3. Audit/rewrite cost becomes hard to control. The expensive parts need budget visibility, retry limits, sampling policy, and graceful degradation.
4. Frontend monitoring becomes too noisy. Logs, alerts, readiness, repair queue, and task failures need one actionable operations surface.
5. Plugin/external review boundaries become risky. Hook failures, file writes, and platform review imports need audit trails and isolation.

### Recommended Evolution Path

#### Phase A: Reliability Baseline, 1 Week

- Finish and verify task state machine, heartbeat, stale recovery, and failure payload contracts.
- Make task monitor show clear next action: retry, resume from checkpoint, fix config, or export logs.
- Keep auto-resume conservative; require explicit user action after restart.

#### Phase B: Fact Source Convergence, 1-2 Weeks

- Declare SQLite narrative tables as continuity truth.
- Declare workspace chapter artifacts as chapter text/report truth.
- Declare YAML as export/compatibility only.
- Ensure list/detail/readiness/repair/export derive from the same source rules.

#### Phase C: Contract Platform, 1 Week

- Add schema/version fields to config and model responses.
- Keep frontend TS utilities aligned with backend response models through contract tests.
- Mark deprecated API paths with replacement and removal window.

#### Phase D: Scale Readiness, 2-4 Weeks

- Introduce a task backend interface with current SQLite/local execution as the default implementation.
- Add long-form benchmarks: 100 mock chapters, 10 project switches, restart during batch, export large book.
- Add budget and audit policy controls for long/epic/infinite factory modes.

#### Phase E: Extension Governance, Ongoing

- Track plugin execution time, exit status, touched files, and failure kind.
- Route external review/imported feedback into the same repair queue as internal gates.
- Keep local-first as the default; only consider PostgreSQL or external queues when multi-user/cloud operation becomes a real requirement.

### Design Space to Reserve Now

- `TaskBackend` interface: `enqueue`, `cancel`, `heartbeat`, `list`, `recover`, `transition`.
- `ChapterArtifactRepository` facade: central place for artifact completeness, trust level, and index sync.
- `ConfigSchemaVersion`: versioned `pipeline.yaml`, `models.json`, and `project_meta.json` migrations.
- `AuditPolicy` interface: sampling, platform-specific rules, budget thresholds, and rewrite policy.
- `VectorBackend` boundary: SQLite, Chroma, local hash, and cloud embeddings behind one readiness/query surface.
- `Actor/AuditTrail`: keep request actor and automated/plugin actions attributable.

## Working Plan

### Milestone 1: Stabilize the Current Batch

- [ ] Run backend targeted reliability tests.
- [ ] Run frontend unit/build checks.
- [ ] Run or document one kill/restart task recovery check.
- [ ] Review `git status` and separate unrelated generated/runtime files from source changes.
- [ ] Split the current work into reviewable commits: task lifecycle, state/artifact contract, error/config contract, frontend helpers.

### Milestone 2: Make Task Recovery User-Trustworthy

- [ ] Confirm all task status writes go through `SQLiteStateStore.update_task_status()`.
- [ ] Confirm long-running phases update heartbeat during quiet periods.
- [ ] Confirm startup cleanup distinguishes no heartbeat, recent interrupted heartbeat, and stale heartbeat.
- [ ] Add UI copy/action for `status_reason` and `resumable_from`.
- [ ] Verify failed/interrupted historical rows are not mutated during retry; retry creates a new task.

### Milestone 3: Collapse Chapter Fact Drift

- [ ] Audit chapter list/detail/readiness/repair/export code paths for duplicated artifact interpretation.
- [ ] Route duplicated checks through `chapter_artifact_status` or index sync.
- [ ] Add missing artifact status tests for any new artifact fields.
- [ ] Update `docs/STATE-SOURCES.md` whenever a new durable artifact is added.

### Milestone 4: Normalize Error Contracts

- [ ] Complete config/model endpoint classification first.
- [ ] Complete task/chapter request failure classification second.
- [ ] Leave assistant snapshot/context fallbacks best-effort unless they are user-triggered actions.
- [ ] Ensure frontend uses `normalizeFailureDetail()` and `formatFailureDetail()` consistently.

### Milestone 5: Keep Complexity From Growing Back

- [ ] When touching `ModelLibrary.vue`, extract one pure helper or child component.
- [ ] When touching `EmbeddingConfig.vue`, keep readiness/action derivation outside template-heavy code.
- [ ] When touching `StateChronicleTab.vue`, keep filtering/grouping logic in tested utilities.
- [ ] Add a simple size watch habit: investigate any active Vue/Python module crossing 900 lines unless it is intentionally generated or test-only.

## Operating Rule

For the next two weeks, every feature change should include one reliability or contract improvement from this plan, except for Milestone 1 and kill/restart validation, which should be completed as dedicated work before more feature expansion.

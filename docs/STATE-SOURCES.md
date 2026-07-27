# State Sources

This project uses several local stores on purpose. The rule is not “one file owns everything”; the rule is that each fact has one authoritative source and the other files are projections or artifacts.

## Source Roles

| Area | Authoritative source | Secondary / derived source | Notes |
|------|----------------------|----------------------------|-------|
| Novel continuity state | SQLite narrative tables | `state/*.yaml` mirror | YAML is compatibility/export surface. New writes should flow through `StateManager` / `SQLiteStateStore`. |
| Manuscript text | SQLite `documents` + `document_revisions` | `chapter_final.txt` compatibility projection | UI editing, publishing and export always read SQLite. Disk text may seed a missing document once; it never overrides a newer document. |
| Chapter plans and reports | `workspace/chapters/chapter_*/` artifacts | SQLite compact chapter index | Plans, audit, gate and checkpoints remain domain artifacts. They do not own manuscript text. |
| Chapter list metadata | SQLite `chapters` index | Artifact/document synchronization | Compact fields such as `word_count`, `has_final`, and `gate_status` are rebuilt from the relevant authoritative source. |
| Task lifecycle | SQLite `tasks` + `task_status_events` | In-memory asyncio tasks | In-memory objects are execution handles only. After restart, SQLite describes what happened. |
| Pending repair / alerts | Checkpoint + retry queue + external review files | Cache files in `workspace/reports/` | Cache files are disposable and must be invalidated when alert inputs change. |
| Prompt and asset versions | SQLite version tables | Markdown/YAML assets on disk | Disk files are editable user assets; version tables preserve history. |
| Vector recall | Configured vector backend | SQLite chapter summaries / artifacts | Readiness must report backend status before long-form continue. |

## Manuscript Contract

`novel_agent.services.manuscript_workspace` owns manuscript reads and writes.

- Save operations use optimistic revision checks.
- Every accepted edit creates a revision before updating the current document.
- Successful writes update the compact chapter index and `chapter_final.txt`
  compatibility projection.
- Publishing and all five exporters read selected SQLite documents in canonical
  chapter order.

## Chapter Artifact Contract

`novel_agent.services.chapter_artifact_status.build_chapter_artifact_status()` is the shared classifier for chapter artifact trust:

- `authoritative`: usable as the current basis for UI, repair, or resume.
- `reference`: useful context, but a later phase should regenerate or revalidate it.
- `stale`: known out of date or unsafe to treat as current state.
- `missing`: expected artifact does not exist or is empty.

The detail API returns the full artifact rows. List and dashboard paths should use compact projections derived from the same rules instead of re-implementing their own interpretation.

## Compact Chapter Index Rules

The SQLite `chapters` table is an index, not the manuscript or full report source.

- `has_final`: true when the SQLite document has non-empty current content (or a
  one-time legacy import supplied it).
- `gate_status = empty`: no final text exists.
- `gate_status = blocked`: unified gate/checkpoint indicates quality block or approval rejection.
- `gate_status = warning`: audit exists with issues or high risk.
- `gate_status = ok`: audit exists and reports no high-risk issue.
- `gate_status = unknown`: not enough reports exist to classify.

If text metadata disagrees with the SQLite document, the document wins. If gate
metadata disagrees with report artifacts, the report artifacts win.

## Recovery Rules

- Task recovery uses `tasks.status_reason`, `tasks.resumable_from`, and `task_status_events`.
- Chapter recovery uses `checkpoint.json`, `reports/unified_gate.json`, and artifact status rows.
- State recovery uses SQLite snapshots/candidates first; YAML mirrors are export/compatibility only.

## YAML Mirror Policy

- `runtime.yaml_mirror_mode` is the explicit policy and may be `write`, `read_only`, or `off`.
- If legacy `runtime.yaml_mirror_enabled` exists, `true` maps to `write` and `false` maps to `off`.
- If neither setting exists, the implicit mode is `read_only`; YAML remains readable for compatibility but SQLite writes are not mirrored automatically.
- `off` is suitable for tests or projects that never need legacy YAML tools.
- On-demand export remains `POST /api/database/export-yaml-mirror`.

## Implementation Guardrails

- Do not directly update `tasks.status`; use `SQLiteStateStore.update_task_status()`.
- Do not derive chapter block state in routes; use services under `novel_agent/services/`.
- Do not treat cache JSON files under `workspace/reports/` as durable state.
- When adding a new artifact, update `chapter_artifact_status.py`, index sync tests, and this document.

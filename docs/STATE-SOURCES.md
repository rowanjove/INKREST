# State Sources

This project uses several local stores on purpose. The rule is not “one file owns everything”; the rule is that each fact has one authoritative source and the other files are projections or artifacts.

## Source Roles

| Area | Authoritative source | Secondary / derived source | Notes |
|------|----------------------|----------------------------|-------|
| Novel continuity state | SQLite narrative tables | `state/*.yaml` mirror | YAML is compatibility/export surface. New writes should flow through `StateManager` / `SQLiteStateStore`. |
| Chapter text and reports | `workspace/chapters/chapter_*/` artifacts | SQLite chapter index | The final text, plan, audit, gate, checkpoint, and reports are the chapter artifact source of truth. |
| Chapter list metadata | SQLite `chapters` index | Disk sync from chapter artifacts | `sync_chapters_from_disk()` rebuilds compact list fields such as `word_count`, `has_final`, and `gate_status`. |
| Task lifecycle | SQLite `tasks` + `task_status_events` | In-memory asyncio tasks | In-memory objects are execution handles only. After restart, SQLite describes what happened. |
| Pending repair / alerts | Checkpoint + retry queue + external review files | Cache files in `workspace/reports/` | Cache files are disposable and must be invalidated when alert inputs change. |
| Prompt and asset versions | SQLite version tables | Markdown/YAML assets on disk | Disk files are editable user assets; version tables preserve history. |
| Vector recall | Configured vector backend | SQLite chapter summaries / artifacts | Readiness must report backend status before long-form continue. |

## Chapter Artifact Contract

`novel_agent.services.chapter_artifact_status.build_chapter_artifact_status()` is the shared classifier for chapter artifact trust:

- `authoritative`: usable as the current basis for UI, repair, or resume.
- `reference`: useful context, but a later phase should regenerate or revalidate it.
- `stale`: known out of date or unsafe to treat as current state.
- `missing`: expected artifact does not exist or is empty.

The detail API returns the full artifact rows. List and dashboard paths should use compact projections derived from the same rules instead of re-implementing their own interpretation.

## Compact Chapter Index Rules

The SQLite `chapters` table is an index, not the full chapter source.

- `has_final`: true when `chapter_final.txt` is non-empty and authoritative/reference according to artifact status.
- `gate_status = empty`: no final text exists.
- `gate_status = blocked`: unified gate/checkpoint indicates quality block or approval rejection.
- `gate_status = warning`: audit exists with issues or high risk.
- `gate_status = ok`: audit exists and reports no high-risk issue.
- `gate_status = unknown`: not enough reports exist to classify.

If the index disagrees with the chapter detail artifact rows, the artifact rows win and the index should be resynced.

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

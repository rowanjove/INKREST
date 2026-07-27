# Task State Machine

This document defines the local task lifecycle for chapter generation, batch runs, gate-only reruns, and novel/arc runs.

## States

| State | Meaning | Terminal |
|-------|---------|----------|
| `pending` | The task has been persisted but the worker has not started useful work. | No |
| `running` | The worker has started and should refresh `last_heartbeat` through status/progress updates. | No |
| `completed` | The task finished and `result` contains the final payload. | Yes |
| `failed` | The task cannot continue automatically. `error`, `status_reason`, and optionally `resumable_from` explain what happened. | Yes |

`aborted` and `queued` are reserved terms for future queue backends. Current abort behavior records `failed` with `status_reason = user_abort` so existing UI and tests keep one terminal failure path.

## Allowed Transitions

| From | To | Typical reason |
|------|----|----------------|
| `pending` | `running` | Worker acquired capacity and started. |
| `pending` | `failed` | Queue timeout, user abort before start, validation failure. |
| `running` | `pending` | Startup recovery after process interruption. |
| `running` | `completed` | Pipeline returned a successful result. |
| `running` | `failed` | Pipeline error or user_abort. |
| `failed` | `pending` | Future retry task only; do not mutate historical failed rows for retry. |

Historical task rows should remain append-only in spirit: retries create a new task id unless a future queue backend explicitly implements resumable jobs.

## Metadata

- `status_reason`: machine-readable reason for the latest status change, for example `startup_cleanup`, `worker_started`, or `user_abort`.
- `resumable_from`: best-known recovery point, usually `current_step`; use `unknown` when no step has been recorded.
- `last_heartbeat`: last time the task made observable progress. It is refreshed by status changes, progress events, step updates, and explicit heartbeats.
- `task_status_events`: append-only transition log with `from_status`, `to_status`, `reason`, and `resumable_from`.

## Startup Recovery

On startup, rows left in `running` are requeued to `pending` with:

- `status_reason = startup_cleanup` when no heartbeat exists yet
- `status_reason = process_interrupted` when the heartbeat is recent but the worker process is gone
- `status_reason = stale_heartbeat` when the heartbeat is older than the cleanup threshold
- `resumable_from = current_step or unknown`

Rows already in `pending` are left untouched. The current background queue may auto-resume standard single-chapter tasks only. Batch, gate-only, novel, and arc tasks are not auto-resumed.

This is intentionally narrow: SQLite records where recovery can begin, and only the simplest single-chapter jobs are eligible for automatic dispatch. Future durable queue work should add explicit `task_type`, claim/lease ownership, and retry attempt fields before broadening auto-resume.

## Implementation Notes

- Use `SQLiteStateStore.update_task_status(...)` for status changes so transition events and heartbeat fields stay consistent.
- Use `SQLiteStateStore.record_task_heartbeat(...)` for long-running work that has not emitted a progress event recently.
- Use `update_task_progress(...)` when a pipeline step emits structured progress; it refreshes `last_heartbeat` and `current_step`.
- Avoid direct SQL updates to `tasks.status` outside store methods.

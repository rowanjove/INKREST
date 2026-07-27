# Error Boundary Audit

Snapshot date: 2026-06-16.

## Hotspots

| Area | Approximate matches | Current role | Recommended treatment |
|------|---------------------|--------------|-----------------------|
| `novel_agent/phases/audit.py` | High | LLM audit/summary/rewrite fallbacks | Keep local fallbacks, but wrap terminal failures with `failure_payload()` when they escape to tasks. |
| `web/routes/assistant.py` | High | Best-effort assistant context assembly | Accept best-effort catches, but classify user-triggered fix/action endpoint failures. |
| `web/routes/config.py` | Medium | Model testing, embedding setup, config helpers | Convert user-facing failures to `http_error_detail()` with `retryable` and `user_action`. |
| `web/tasks.py` | Medium | Task lifecycle boundary | Continue routing task failures through `task_failure_result()`. Avoid direct `update_task_status(..., "failed", str(exc))` for new paths. |
| `web/routes/chapters/*` | Medium | Chapter CRUD, rewrite, versions, extras | Keep artifact cleanup best-effort catches, classify request-facing failures. |
| `web/model_library.py` | Low | Model file compatibility | Keep defensive parsing, surface save/delete failures through config routes. |

## Contract

Backend failure payloads now carry:

- `code`
- `failure_kind`
- `failure_hint`
- `message`
- `retryable`
- `user_action`
- optional `resumable_from`

Frontend formatting should use `normalizeFailureDetail()` and `formatFailureDetail()` from `web/frontend/src/utils/errorCodes.ts`.

## Next Refactor Order

1. `web/routes/config.py`: model test/setup endpoints, because users immediately need actionable auth/rate-limit/network feedback.
2. `web/routes/chapters/tasks.py`: classify `ValueError`/pipeline failures into `http_error_detail()`.
3. `web/tasks.py`: keep closing the remaining direct `failed` writes; abort and batch failures now carry lifecycle metadata.
4. `web/routes/assistant.py`: classify only user-triggered action endpoints; leave snapshot context assembly best-effort.

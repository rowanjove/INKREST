# Changelog

## Unreleased — Performance (Phase 0–4)

### Backend

- Progress summary 3s TTL cache; pipeline alerts disk cache; batch-status dedupe
- Task progress writes debounced (500ms per task+step)
- Calibration / scale-profile use SQLite chapter index with disk sync fallback
- `progress_snapshot.json` materialized for lightweight project list stats
- `list_projects` uses indexed chapter/word counts instead of full-disk glob
- Incremental `sync_chapters_from_disk` via mtime manifest
- WebSocket `/ws/tasks` pushes task list on change (coalesced ~350ms)

### Frontend

- `pollingGate` + `pollingHub`: skip polls when tab hidden; shared poll timers
- TaskLog reads `tasksStore.taskList`; shallow log/task reactivity
- Monitor lazy tabs; Dashboard adaptive refresh (3s running / 15s idle)
- Element Plus on-demand auto-import
- WS connected时停止 2s 任务 HTTP 轮询，失败才降级

### Tooling / CI

- `npm run build:analyze` — Rollup bundle visualizer (`dist/bundle-stats.html`)
- `scripts/check_frontend_bundle.py` + `benchmarks/frontend_bundle_budget.json`
- `scripts/perf_api_baseline.py` + `benchmarks/api_perf_baseline.json`
- CI: bundle budget + API perf checks after frontend build
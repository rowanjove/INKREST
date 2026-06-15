# Codex Project Guide

This repository is a local-first novel generation agent: Python/FastAPI backend, Vue 3 + Electron desktop frontend, SQLite state, prompt/preset assets, and a first-party plugin system.

## Default Plugin Setup

- Use `superpowers` for non-trivial feature work, debugging, TDD, planning, review, and branch finishing. This project already keeps specs and plans under `docs/superpowers/`, so continue that style for large changes.
- Use `build-web-apps` plus `browser` for frontend UI work in `web/frontend`, especially layout, interaction, local visual QA, Playwright-style checks, and Electron-facing screens.
- Use the project MCP server `novel_agent` for read-only status checks: project list, generation snapshot, pending chapters, pipeline alerts, runtime/file logs. It is configured in Codex as offline by default to avoid slow localhost probes when the backend is not running.
- Use `github` when working with PRs, CI failures, review comments, issue triage, or publishing a branch.
- Keep `figma`, `canva`, `netlify`, and `cloudflare` installed but use them only when the task explicitly touches design handoff, marketing/design assets, deployment, or Cloudflare infrastructure.
- Prefer `computer-use` only for Windows desktop automation that cannot be handled through shell, Browser, or repository tools.

## Repository Workflow

- Read local docs before changing behavior: `PROJECT.md`, `PROJECT_STRUCTURE.md`, `CONTRIBUTING.md`, and relevant files in `docs/superpowers/`.
- Do not auto-trigger novel generation (`continue-novel`, `run-chapter`, batch runs) without explicit user approval. Status/log reads are fine.
- Treat `workspace/`, `projects/`, `state/`, `data/`, `logs/`, `dist*`, `build/`, and packaged Electron artifacts as runtime/generated unless the task is specifically about them.
- Never commit secrets. `config/pipeline.yaml`, `config/models.json`, and `.env` are local configuration.
- There may be user changes in progress. Check `git status` and preserve unrelated edits.

## Verification Shortcuts

- Backend-only changes: `python -m pytest tests/ --ignore=tests/smoke -q --tb=short`
- Frontend-only changes: from `web/frontend`, run `npm run test:unit` and `npm run build`; then run `python -m pytest tests/test_workspace_ui_contract.py -q` from the repo root when UI contracts are touched.
- Release or packaging work: from `web/frontend`, run `npm run build`, `npm run check:bundle`, and the relevant Electron packaging command; then verify the bundle manifest when applicable.
- MCP status checks: use the configured `novel_agent` MCP tools, or fall back to `py -3.12 -m mcp_server.server` / `python cli.py agent snapshot --novel-root <repo>`.

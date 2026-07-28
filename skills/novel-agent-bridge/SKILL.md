---
name: novel-agent-bridge
description: Query Novel Agent workspace status, progress, pending chapters, pipeline alerts, and logs via CLI, HTTP, or MCP. Use when the user asks about novel generation agent state, 全书进度, 流水线日志, readiness, batch status, or integrating Cursor/Grok agents with this project.
---

# Novel Agent Bridge

## When to use

- User wants **status / progress / pending / readiness** without opening the UI
- User wants **runtime or file logs** from the novel pipeline
- User asks to wire **CLI, MCP, or skill** for external AI agents

## Quick paths

### 1. MCP (preferred when configured)

Server: `python -m mcp_server.server` from project root.

Tools: `novel_agent_snapshot`, `novel_agent_file_logs`, `novel_agent_runtime_logs`, `novel_agent_pipeline_alerts`, `novel_agent_list_projects`.

Set `NOVEL_AGENT_ROOT` to workspace root; set `NOVEL_AGENT_API_URL` if backend is running.

### 2. CLI (scriptable JSON)

```bash
python cli.py agent snapshot --novel-root <workspace>
python cli.py agent logs --root-dir projects/<id> --lines 80
python cli.py agent snapshot --http   # needs NOVEL_AGENT_API_URL
python cli.py agent logs --runtime
python cli.py agent alerts
```

### 3. HTTP (curl / fetch)

- `GET /api/agent/snapshot`
- `GET /api/agent/logs/tail?lines=80`
- `GET /api/runtime-logs`
- `GET /api/pipeline-alerts`

Header `X-Novel-Agent-Token` if `NOVEL_AGENT_ACCESS_TOKEN` is set.

## Interpretation hints

- **Authoritative chapter count**: `progress_summary.authoritative_completed` (not raw ledger alone)
- **Blocked continue**: check `readiness` and `pending`; fix outline/stale before `continue`
- **Paused batch**: `batch.paused` + `pause_reason` in snapshot

## Do not (v1)

- Auto-trigger `continue-novel` or `run-chapter` without explicit user approval
- Assume HTTP works when server is down — fall back to offline `agent snapshot` / `file_logs`

## Full reference

See [docs/AGENT-INTEGRATION.md](../../docs/AGENT-INTEGRATION.md).
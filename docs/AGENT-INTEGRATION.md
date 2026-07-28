# AI Agent 接入（CLI / MCP / HTTP / Skill）

外部 Agent（Cursor、Grok、Claude Code 等）可通过只读接口查看全书进度、待处理章节、就绪门禁与日志，无需打开 UI。

## 环境变量

| 变量 | 说明 |
|------|------|
| `NOVEL_AGENT_ROOT` | 工作区根目录（含 `projects.json`），离线 CLI/MCP 用 |
| `NOVEL_AGENT_API_URL` | 运行中后端，默认 `http://127.0.0.1:8000` |
| `NOVEL_AGENT_ACCESS_TOKEN` | 与 UI 一致时设置，请求头 `X-Novel-Agent-Token` |
| `NOVEL_AGENT_MCP_MODE` | `auto`（能连 API 则用 HTTP）/ `offline` / `http` |

## CLI（JSON  stdout）

```bash
# 列出项目
python cli.py agent projects --novel-root D:\path\to\novel-agent

# 离线快照（进度、pending、readiness）
python cli.py agent snapshot --novel-root ... --project-id <id>

# 连运行中服务
set NOVEL_AGENT_API_URL=http://127.0.0.1:8000
python cli.py agent snapshot --http

# 磁盘日志
python cli.py agent logs --root-dir projects\<id> --lines 100

# 内存流水线日志（需后端在跑）
python cli.py agent logs --runtime --lines 50

# 流水线告警、健康检查
python cli.py agent alerts
python cli.py agent health
```

## HTTP API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/agent/projects` | 项目列表 |
| GET | `/api/agent/snapshot` | 聚合状态（含最近 runtime_logs） |
| GET | `/api/agent/logs/tail?lines=80` | 项目 `logs/novel_agent.log` 尾部 |
| GET | `/api/runtime-logs` | 运行中流水线日志（已有） |
| GET | `/api/pipeline-alerts` | 告警（已有） |
| GET | `/api/chapters/tasks` | 章节任务（已有） |

写操作（`continue`、`run-chapter`）仍走原有 API，并受 `409` 并发锁、`NOVEL_AGENT_DEBUG_RUN`、外审门禁等约束；Agent 集成 v1 仅推荐只读。

## MCP Server

安装依赖后启动：

```bash
pip install -r requirements-mcp.txt
python -m mcp_server.server
```

也可在应用内 **设置 → AI Agent 接入** 查看路径、复制 MCP/CLI 配置并测试快照 API。

### Cursor / Grok 配置示例

在 MCP 配置中增加（路径按本机修改）：

```json
{
  "mcpServers": {
    "novel-agent": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "F:\\AI\\vibecoding\\小说生成agent",
      "env": {
        "NOVEL_AGENT_ROOT": "F:\\AI\\vibecoding\\小说生成agent",
        "NOVEL_AGENT_API_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

### 工具一览

- `novel_agent_health` — 健康检查
- `novel_agent_list_projects` — 项目列表
- `novel_agent_snapshot` — 全书状态快照
- `novel_agent_runtime_logs` — 内存流水线日志（需后端）
- `novel_agent_file_logs` — 磁盘日志（可离线）
- `novel_agent_pipeline_alerts` — 流水线告警
- `novel_agent_tasks` — 章节任务列表

## Skill

项目内 Skill：`skills/novel-agent-bridge/SKILL.md`。在对话中提及「查小说 agent 状态」「读 novel 日志」时会引导 Agent 使用上述 CLI/MCP。

## 安全说明

- 默认只读；勿在未确认时让 Agent 自动 `continue-novel`。
- 生产环境请设置 `NOVEL_AGENT_ACCESS_TOKEN`。
- MCP 以 stdio 运行，勿把 API Key 写入 MCP env 并提交仓库。

# 远程部署安全说明

栖墨默认在 `127.0.0.1` 上提供 API，仅本机可访问。若需在局域网或服务器上远程使用，请遵循以下约定。

## 启动远程服务

```bash
python main.py serve --host 0.0.0.0 --port 8000 --allow-remote
```

- 必须同时指定 `--allow-remote` 与非 loopback 的 `--host`，否则进程会拒绝启动。
- 首次远程启动会自动生成 `NOVEL_AGENT_ACCESS_TOKEN` 并打印到控制台；请妥善保存。

也可手动设置环境变量后再启动：

```bash
set NOVEL_AGENT_ACCESS_TOKEN=<your-secret-token>
set NOVEL_AGENT_ALLOW_REMOTE=1
set NOVEL_AGENT_HOST=0.0.0.0
python main.py serve --host 0.0.0.0 --allow-remote
```

## 客户端鉴权

所有 `/api/*` 请求（健康检查 `/api/health` 除外）须在 HTTP 头中携带：

```
X-Novel-Agent-Token: <token>
```

WebSocket `/ws/tasks` **仅**接受上述 Header 中的令牌，**不要**在 URL 查询参数中传递 token（避免出现在代理日志与浏览器历史中）。

前端可在本地存储键 `novel-agent-access-token` 中保存令牌；Axios 拦截器会自动附加 Header。

## 不建议的配置

- 不要将服务直接暴露到公网而无 TLS 与防火墙；优先使用 VPN 或反向代理（HTTPS）。
- 不要使用 `uvicorn --workers N` 多 worker：应用状态（当前项目、任务表）为单进程内存模型。
- 不要启用来源不明的插件：插件在本机执行 Python，等同于安装第三方程序。

## 调试模式

设置 `NOVEL_AGENT_DEBUG=1` 时，500 错误响应可能包含内部异常文本。生产远程部署请勿开启。
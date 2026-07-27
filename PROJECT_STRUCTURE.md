# 栖墨 V2 代码结构

> 更新：2026-07-27。运行数据与构建产物不属于源码结构。

## 顶层目录

```text
.
├── main.py / cli.py                  # 服务与 CLI 入口
├── novel_agent/                      # Python 领域、流水线与基础设施
│   ├── agents/                       # 专职 Agent
│   ├── domain/                       # 任务、正文、发布等领域对象
│   ├── exporters/                    # 五格式导出器
│   ├── phases/                       # 生成/审校阶段
│   ├── plugins/                      # 第一方插件系统与权限
│   ├── services/                     # 应用服务与聚合读模型
│   └── state/                        # SQLite 仓储、schema 与 YAML 投影
├── web/
│   ├── app.py                        # FastAPI 装配
│   ├── context.py                    # 项目/任务/插件作用域
│   ├── project_manager.py            # 项目注册与文件生命周期
│   ├── routes/                       # HTTP 端点
│   └── frontend/
│       ├── src/                      # Vue 应用
│       ├── electron/                 # Electron 主进程与 preload
│       ├── e2e/                      # Playwright
│       └── scripts/                  # 打包后烟测
├── prompts/ / assets/ / presets/     # 内置模板
├── scripts/                          # 构建、校验与性能工具
├── tests/                            # 后端/契约测试
└── docs/                             # 架构、规范、阶段计划
```

`projects/`、`workspace/`、`state/`、`data/`、`logs/`、`build/`、
`dist*` 和 Electron 打包目录是运行时/生成物，默认不提交。

## 后端分层

### HTTP 与应用上下文

- `web/app.py`：中间件、异常边界、路由装配和静态前端。
- `web/context.py`：当前项目、项目级 `TaskManager`、插件管理器。
- `web/lifespan.py`：启动恢复与广播循环；不自动迁移根级旧数据。
- `web/routes/projects.py`：项目、备份、V2 重置与导入导出。
- `web/routes/manuscript.py`：SQLite 正文与修订。
- `web/routes/production.py`：生产中心聚合与操作。
- `web/routes/publishing.py`：发布工作区、预检和五格式导出。
- `web/routes/config.py` / `plugins.py`：设置、模型和插件权限。

### 领域与服务

- `novel_agent/domain/`：无 UI 依赖的类型与规则。
- `novel_agent/services/project_snapshot.py`：概览统一快照。
- `novel_agent/services/planning_workspace.py`：策划聚合。
- `novel_agent/services/manuscript_workspace.py`：正文真源、并发版本与投影。
- `novel_agent/services/production_workspace.py`：运行/修复/费用/日志读模型。
- `novel_agent/services/publishing_workspace.py`：发布预览与预检。
- `novel_agent/services/v2_reset.py`：去密钥备份和原子项目重置。

### 存储

- `novel_agent/state/sqlite_store.py`：统一仓储入口。
- `manuscript_repository.py`：正文与修订。
- `task_repository.py`：任务、租约和状态事件。
- `state_repository.py`：叙事状态。
- `yaml_mirror.py`：可关闭的兼容投影。
- `schema_version.py`：显式 V2 schema 检测；不静默升级旧库。

## 前端分层

```text
src/
├── app/            # 壳、路由元数据、命令与诊断
├── views/          # 九个产品入口的页面容器
├── components/     # 按 planning/manuscript/production/publishing/config 分组
├── entities/       # API DTO 到 UI 模型的纯转换
├── features/       # 跨组件业务流
├── composables/    # 生命周期与交互状态
├── stores/         # 项目、快照、任务、告警、杉杉
├── shared/ui/      # 小型视觉原语
└── api/            # HTTP transport 与领域 API
```

页面容器负责组合，不自行推导后端状态。跨页面项目状态来自
`useProjectStore` 与 `useProjectSnapshotStore`；任务传输由 WebSocket
主通道和 HTTP 兜底组成。

## Electron 边界

- `electron/main.ts`：唯一主入口、单实例、后端 sidecar 生命周期。
- `electron/preload.ts`：最小 IPC 白名单。
- `electron/window-security.ts`：导航、窗口和外链策略。
- `electron/ipc/pet-ipc.ts`：杉杉窗口受控 IPC。
- 渲染进程启用 `contextIsolation`、禁用 Node integration。

Knip 配置显式列出 Electron 多入口；不要因普通 SPA 静态分析误删这些文件。

## 关键 API

| 能力 | API |
|---|---|
| 项目 | `/api/projects` |
| 项目快照 | `/api/projects/current/snapshot` |
| 策划聚合 | `/api/planning/workspace` |
| 正文 | `/api/manuscript/*` |
| 生产 | `/api/production/*` |
| 发布 | `/api/publishing/*` |
| 备份 | `POST /api/projects/{id}/backup` |
| V2 重置 | `POST /api/projects/{id}/reset-v2` |
| 插件 | `/api/plugins/*` |

实际契约以路由、Pydantic 模型和测试为准，不在多个文档复制完整端点清单。

## 修改守则

- 新业务逻辑优先进入 `novel_agent/services/`，路由保持薄。
- 正文、任务和叙事状态只经 SQLite 仓储写入。
- 不从派生文件反向覆盖 SQLite 新数据。
- 不在页面加载时触发生成。
- 项目破坏性操作必须精确到注册项目、检查活跃任务并先备份。
- 新页面应复用现有工作区和 UI 原语，避免再建功能重复入口。

# Factory 模式 ↔ 运行时映射

> 单一来源：`novel_agent/control/factory_policy.py`（行为）+ `web/factory_modes.json`（文案）  
> 仅当 `config/project_meta.json` **显式写入** `factory_mode` 时生效；未设置则保持旧版默认流水线。

| 模式 ID | 中文名 | 门禁 | 自动改写 | 审校档 | 向量长篇 | 续跑熔断 |
|---------|--------|------|----------|--------|----------|----------|
| `newbie_auto` | 新手全自动 | `block_on_fail` | 开 | 默认 | 按体量 | 默认 |
| `author_copilot` | 作者协作 | `report_only` | 关 | standard | 按体量 | 默认 |
| `platform_review` | 平台过审 | `block_on_fail` | 开 | premium | 按体量 | 默认 |
| `longform_stable` | 长篇稳定 | `block_on_fail` | 开 | premium | **stub 时阻断 continue** | 默认 |
| `studio` | 工作室生产 | `block_on_fail` | 开 | 默认 | 按体量 | 批次失败 3 次熔断 |

## 相关配置

`config/pipeline.yaml` → `runtime`：

- `yaml_mirror_mode`：`write`（默认）| `read_only` | `off` — 控制 `state/*.yaml` 双写；`read_only` 时 SQLite 为唯一写入源，仍可读旧 YAML 并做漂移检查
- `yaml_mirror_enabled`（遗留布尔）：`true`→`write`，`false`→`off`；未设置 `yaml_mirror_mode` 时生效
- `vector_readiness`：`auto` | `block` | `warn` | `ignore` — 覆盖长篇向量 stub 时的阻断/警告策略

### 长篇向量存储（ChromaDB）

`long` / `epic` / `infinite`（或 `target_chapters >= 100`）且未在 `embedding.backend` 中显式指定时，运行时自动将向量存储后端设为 `chromadb`（需安装 `chromadb` 包；`provider: stub` 仍可用本地哈希向量写入 Chroma）。

显式写 `embedding.backend: sqlite` 可保留 SQLite 向量表。`/api/novel/readiness` 返回 `embedding_backend`、`chromadb_available`。

### 项目级任务队列

每本书独立 `TaskManager`（`web/project_task_registry.py`），切换书库不会销毁另一本书的后台章节任务。

`config/pipeline.yaml` → `runtime`：

- `max_concurrent_chapters`（默认：短篇 2、长篇 1）：Web 层同时运行的章节任务数
- `max_workers`：单章内并行场景数（生成阶段 ThreadPool）

`GET /api/chapters/tasks/queue` 返回当前项目的队列快照与并发上限。

### 请求级项目上下文

高风险与书级 API 统一注入 `ProjectSession`（`web/deps.py`）：`project_id`、`root_dir`、可选 `actor_id`（请求头 `X-Novel-Agent-Actor`，默认 `local`）。写操作路由使用 `RequireProjectDep`（无打开的书则 400）。

### YAML 只读导出

`read_only` 或需要一次性对齐磁盘时，调用 `POST /api/database/export-yaml-mirror`，从 SQLite 导出 `events/objects/foreshadows/hooks` 到 `state/*.yaml`（不恢复实时双写）。

## 验证

- 行为差异：`pytest tests/test_factory_mode_policy.py -q`
- Dashboard 聚合：`pytest tests/api/test_factory_dashboard.py -q`
- 开书清单 / continue 门禁：`pytest tests/api/test_api_novel_readiness.py -q`
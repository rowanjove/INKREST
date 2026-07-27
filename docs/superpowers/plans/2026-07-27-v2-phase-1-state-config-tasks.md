# 栖墨 V2 Phase 1 状态、配置与任务内核 Implementation Plan

**Goal:** 建立 V2 的统一项目快照、显式配置 schema、可恢复任务状态机和安全数据重置边界，让后续页面只消费稳定 API 契约。

**Architecture:** 保留“每本书一个 SQLite”隔离方式，但将任务、章节索引和故事实体明确视为 SQLite 真相源。任务领域模型独立于 Web 与 SQLite，所有状态变更先经过状态机；SQLite 使用 claim token、lease 和 heartbeat 支持恢复。配置以 Pydantic schema 校验，YAML 仅是序列化格式。`ProjectSnapshot` 由一个服务聚合，HTTP、MCP 与后续 Pinia store 共用同一 DTO。

**Compatibility:** 用户已批准清空旧数据。V2 不迁移旧任务记录，也不从 `goal` 猜测任务类型；发现旧 schema 时只报告“需要重置”，由带确认词的显式 API 执行备份与初始化。

**Tech Stack:** Python 3.11/3.12、Pydantic v2、SQLite、FastAPI、pytest、Vue 3、TypeScript

---

## Task 1：建立 V2 领域契约

**Files:**

- Create: `novel_agent/domain/__init__.py`
- Create: `novel_agent/domain/tasks.py`
- Create: `novel_agent/domain/project_snapshot.py`
- Create: `tests/test_v2_domain_contracts.py`

- [x] **Step 1: 写失败的任务状态机测试**

覆盖：

- `pending -> claimed -> running -> succeeded`
- `running -> paused -> claimed`
- `pending/claimed/running/paused -> cancelled`
- `failed -> claimed` 仅在 `attempt < max_attempts`
- 所有终态不能再次转移
- 未知状态和非法转移抛出明确的领域异常

- [x] **Step 2: 写失败的 DTO 序列化测试**

`TaskRecord` 必须包含设计中的全部字段；`ProjectSnapshot` 必须包含：

```text
project
workflow_mode
readiness
outline_progress
chapter_progress
active_tasks
blocking_issues
quality_summary
cost_summary
next_actions
updated_at
```

- [x] **Step 3: 实现领域枚举、转移函数和 Pydantic DTO**

任务状态固定为：

```text
pending, claimed, running, paused, succeeded, failed, cancelled
```

任务类型使用显式枚举，至少包含：

```text
chapter, chapter_batch, novel_plan, chapter_plan, novel_run,
novel_continue, novel_autopilot, embedding_setup, export
```

- [x] **Step 4: 验证并提交**

```powershell
py -3.12 -m pytest tests/test_v2_domain_contracts.py -q --tb=short
py -3.12 -m ruff check novel_agent web tests
git commit -m "feat: define v2 task and snapshot contracts"
```

## Task 2：建立版本化 SQLite 任务仓储

**Files:**

- Create: `novel_agent/state/schema_version.py`
- Create: `novel_agent/state/task_repository.py`
- Modify: `novel_agent/state/sqlite_schema.py`
- Modify: `novel_agent/state/sqlite_store.py`
- Modify: `tests/test_state_candidates.py`
- Create: `tests/test_v2_task_repository.py`

- [x] **Step 1: 写失败的 schema 与仓储测试**

覆盖：

- 新数据库写入 `schema_version = 2`
- `tasks` 表含设计中的全部列和索引
- 旧数据库被识别为 `legacy`，不静默改写
- 创建任务必须显式传 `project_id`、`task_type`、`payload`
- 同一 `id` 与相同 payload 幂等，payload 不同则冲突

- [x] **Step 2: 写失败的 claim / lease / heartbeat 测试**

覆盖：

- 只有 `pending` 或可重试 `failed` 能 claim
- claim 原子增加 attempt 并生成 token
- 非持有者不能 start、heartbeat、complete
- lease 过期的 `claimed/running` 可恢复到 `pending`
- heartbeat 延长 lease
- `result_json`、`checkpoint` 与 `status_reason` 可往返

- [x] **Step 3: 实现 V2 schema 版本和 TaskRepository**

新任务列：

```text
id, project_id, task_type, status, payload_json, result_json,
attempt, max_attempts, claim_token, lease_expires_at, heartbeat_at,
checkpoint, status_reason, created_at, started_at, finished_at
```

所有写入使用事务与条件更新；JSON 以对象校验后序列化。

- [x] **Step 4: 让 SQLiteStateStore 组合新仓储**

`SQLiteStateStore.task_repository` 作为 V2 唯一任务写入入口。旧方法暂留到
Task 3 同一次执行器迁移中删除，避免仓储提交与调用方提交之间出现不可运行
状态；查询 DTO 将从 payload 派生 `chapter_id`、`goal`、`dry_run`。

- [x] **Step 5: 验证并提交**

```powershell
py -3.12 -m pytest tests/test_v2_task_repository.py tests/test_state_candidates.py -q --tb=short
git commit -m "feat: add leased v2 task repository"
```

## Task 3：把后台执行器接入 V2 状态机

**Files:**

- Modify: `novel_agent/progress.py`
- Modify: `web/tasks.py`
- Modify: `web/tasks_autopilot.py`
- Modify: `web/routes/chapters/tasks.py`
- Modify: `web/models.py`
- Modify: `tests/test_project_task_registry.py`
- Modify: `tests/api/test_api_tasks.py`
- Modify: `tests/test_batch_retry_queue.py`
- Modify: `web/frontend/src/stores/chapter.ts`
- Modify: `web/frontend/src/stores/tasks.ts`
- Modify: `web/frontend/src/components/TaskLog.vue`

- [x] **Step 1: 写失败的执行器接入测试**

覆盖：

- submit 写入显式 task type 和 payload
- worker 先 claim 再 running，结束为 succeeded/failed/cancelled
- 相同 id 重放不会启动第二个协程
- 进度事件总带 `project_id` 与 `task_id`
- abort 转换为 cancelled，不再返回 `aborted`
- 启动恢复只回收 lease 已过期任务

- [x] **Step 2: 在进度上下文加入项目与任务身份**

扩展现有 ContextVar 包装器，不引入可覆盖的全局回调。所有 emit 函数自动
补充 `project_id` 和 `task_id`。

- [x] **Step 3: 迁移所有 TaskManager 与 autopilot 调用**

每条提交路径显式指定 `TaskType`；worker 持有 claim token；状态写入只能
通过仓储转移函数完成。删除从 `goal`、`chapter_id` 或 task id 前缀猜类型的代码。

- [x] **Step 4: 更新 API 与前端临时消费者**

HTTP 与 TypeScript 状态统一为 V2 枚举。用户界面继续显示中文标签，不暴露
内部英文值。

- [x] **Step 5: 验证并提交**

```powershell
py -3.12 -m pytest tests/test_project_task_registry.py tests/api/test_api_tasks.py tests/test_batch_retry_queue.py tests/test_full_chain_chaos.py -q --tb=short
npm run test:unit --prefix web/frontend
git commit -m "refactor: run background work through v2 task state machine"
```

Actual: 聚焦回归 48 passed、5 subtests passed；后端全量 775 passed、
4 skipped、10 subtests passed；前端 143 tests 与生产构建通过。

## Task 4：建立 Pydantic 配置真相源与原子写入

**Files:**

- Create: `novel_agent/config/__init__.py`
- Create: `novel_agent/config/schema.py`
- Create: `novel_agent/config/io.py`
- Modify: `novel_agent/pipeline.py`
- Modify: `web/routes/config.py`
- Modify: `web/model_library.py`
- Modify: `web/preset_manager.py`
- Modify: `web/routes/outlines.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/api/test_api_config.py`
- Create: `tests/test_v2_config_schema.py`

- [x] **Step 1: 写失败的配置解析测试**

覆盖：

- 默认配置通过 schema
- 缺失 `schema_version` 的新写入被补为 2
- YAML 语法错误、非对象根节点和范围错误抛出 `ConfigValidationError`
- 未设置的 `${ENV}` 不再静默替换为空字符串
- API 返回结构化错误路径，不回退到空配置

- [x] **Step 2: 写失败的原子写入测试**

模拟替换失败时原文件不变；成功后不存在临时文件；密钥字段不出现在日志、
异常消息和普通 GET 响应中。

- [x] **Step 3: 实现宽进严出的 Pydantic schema**

覆盖 runtime、chapter、quality、llm、embedding；已知字段严格验证，插件
扩展字段允许保留。schema 版本固定为 2。

- [x] **Step 4: 统一所有 pipeline.yaml 读写入口**

所有业务模块调用 `load_pipeline_document()` / `write_pipeline_document()`；
写入使用同目录临时文件、flush、fsync 与 `os.replace()`。

- [x] **Step 5: 提供配置 schema API**

新增 `GET /api/config/schema`，供 Phase 2 表单元数据消费。普通 GET 始终
脱敏；高级源码模式单独返回无密钥文档。

- [x] **Step 6: 验证并提交**

```powershell
py -3.12 -m pytest tests/test_v2_config_schema.py tests/test_pipeline.py tests/api/test_api_config.py tests/test_model_slots.py tests/test_pipeline_global_settings.py -q --tb=short
git commit -m "refactor: make pydantic the configuration source of truth"
```

Actual: 配置与相关 API/模型/项目回归 128 passed；Ruff 全量检查通过。

## Task 5：提供统一 ProjectSnapshot

**Files:**

- Create: `novel_agent/services/project_snapshot.py`
- Modify: `web/routes/projects.py`
- Modify: `web/routes/agent_api.py`
- Modify: `novel_agent/integrations/agent_bridge.py`
- Create: `tests/test_project_snapshot.py`
- Modify: `tests/test_agent_bridge.py`
- Modify: `tests/api/test_api_projects.py`

- [ ] **Step 1: 写失败的快照聚合测试**

使用临时项目创建大纲、章节索引、任务、质量与费用数据，断言所有一级字段
存在、时间为 ISO 8601、active tasks 只含活跃状态、next actions 可执行。

- [ ] **Step 2: 实现单一聚合服务**

聚合现有 readiness、progress summary、outline、任务仓储、质量报告和费用
统计。字段缺失应返回稳定空结构；配置无效则进入 blocking issues，不能静默。

- [ ] **Step 3: 接入 HTTP 与 agent bridge**

新增：

```text
GET /api/projects/current/snapshot
GET /api/projects/{project_id}/snapshot
```

`/api/agent/snapshot` 在保留日志提示的同时复用同一项目快照，不再重复拼装
业务状态。

- [ ] **Step 4: 验证并提交**

```powershell
py -3.12 -m pytest tests/test_project_snapshot.py tests/test_agent_bridge.py tests/api/test_api_projects.py -q --tb=short
git commit -m "feat: expose a unified project snapshot"
```

## Task 6：实现显式、安全的 V2 数据重置

**Files:**

- Create: `novel_agent/services/v2_reset.py`
- Modify: `web/routes/projects.py`
- Modify: `web/models.py`
- Create: `tests/test_v2_reset.py`
- Modify: `tests/api/test_api_projects.py`

- [ ] **Step 1: 写失败的安全边界测试**

覆盖：

- 缺少精确确认词返回 400
- 项目有活跃任务返回 409
- 路径不在解析后的 `projects/` 下时拒绝
- 备份 zip 不包含密钥、日志、插件和外部符号链接
- 重置只清理目标项目运行时目录
- 初始化后 schema version 为 2，项目仍可正常打开

- [ ] **Step 2: 实现备份与重置服务**

提供“仅备份”和“备份后重置”两个显式动作；先生成可验证 zip，再在项目锁内
重建数据库和最小目录。任何失败都不修改原项目。

- [ ] **Step 3: 提供 API**

```text
POST /api/projects/{project_id}/backup
POST /api/projects/{project_id}/reset-v2
```

确认词必须包含目标 project id，避免误操作。

- [ ] **Step 4: 验证并提交**

```powershell
py -3.12 -m pytest tests/test_v2_reset.py tests/api/test_api_projects.py tests/test_security_regressions.py -q --tb=short
git commit -m "feat: add explicit v2 backup and reset flow"
```

## Task 7：Phase 1 全量验收

**Files:**

- Modify: `docs/superpowers/plans/2026-07-27-v2-phase-1-state-config-tasks.md`

- [ ] **Step 1: 后端全量**

```powershell
py -3.12 -m ruff check novel_agent web tests
py -3.12 -m pytest tests/ --ignore=tests/smoke -q --tb=short
py -3.12 scripts/perf_api_baseline.py --check
```

- [ ] **Step 2: 前端与 Electron**

```powershell
npm run test:unit --prefix web/frontend
npm run test:electron --prefix web/frontend
npm run build --prefix web/frontend
npm run build:electron --prefix web/frontend
npm run check:bundle --prefix web/frontend
npm run audit:prod --prefix web/frontend
```

- [ ] **Step 3: 记录实际结果并提交**

```powershell
git commit -m "docs: record v2 phase 1 verification"
```

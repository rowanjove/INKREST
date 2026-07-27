# 下一阶段技术顾问行动计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` when turning any item below into code. This document is an advisory plan: diagnose first, then split selected work into implementation checklists before editing.

**Goal:** 把当前项目从“功能快速堆叠完成度高”推进到“长任务可靠、状态可信、接口契约稳定、可支撑更大体量创作”的工程状态。

**Architecture:** 保持本地优先、FastAPI + Vue/Electron + SQLite 的现有方向，不做一步到位的大重构。优先收敛状态一致性、长任务可恢复、配置契约、异常可观测和前端大组件复杂度。

**Tech Stack:** Python/FastAPI, SQLite, Vue 3/TypeScript, Electron, pytest, Vitest, Playwright, project-level task registry, Factory runtime policy.

---

## 依据与现状

- 文档显示上一轮 `PLAN-TECH-ADVISORY-2026Q2.md` 和 `IMPROVEMENT-ROADMAP-2026Q2.md` 的硬化项大多已完成：Factory runtime、项目级 TaskManager、YAML mirror mode、readiness、前端 API 域拆分、E2E/Vitest/chaos 等已有基础。
- 当前代码规模约：`novel_agent` 143 个源码文件 / 22.8k 行，`web` 327 个源码文件 / 62.3k 行，`web/frontend/src` 246 个源码文件 / 47.0k 行，`tests` 113 个文件 / 15.2k 行。
- 最大复杂度集中在：`novel_agent/phases/audit.py`、`novel_agent/state/vector_store.py`、`web/tasks.py`、`web/routes/projects.py`、`web/routes/outlines.py`、`web/routes/config.py`、`web/routes/assistant.py`，以及前端 `StateChronicleTab.vue`、`ModelLibrary.vue`、`App.vue`、`EmbeddingConfig.vue`、`PendingChaptersPanel.vue`。
- 仓库仍保留较多兼容层和宽异常捕获：YAML mirror、legacy root fallback、deprecated chapter APIs、`except Exception` 分布在任务、路由、状态、向量、审计、插件等路径。

## 第一层：现状诊断

### 1. 最严重的 3 个问题

1. **长任务生命周期仍偏内存态，恢复语义不够强**
   - 影响范围：连写、批量章节、修章、Electron 断线、项目切换。
   - 修复难度：中等。已有 SQLite task 表和 project task registry，但运行中的 asyncio task、abort set、running chapter map 仍在进程内。
   - 优先级：最高。它直接决定“跑 20 章、100 章、断电重启后是否可信”。

2. **状态与产物有多源事实，SQLite、YAML、workspace artifact、chapter index 之间仍需要更强的契约**
   - 影响范围：连续性、章节列表、修章队列、导出、readiness、用户信任。
   - 修复难度：中等偏高。不是单点 bug，而是事实来源边界不够硬。
   - 优先级：很高。内容生成类产品最怕“看起来完成，但状态悄悄漂移”。

3. **接口和配置演进速度快，契约层还不够集中**
   - 影响范围：前后端同步、Electron 打包、旧 API 兼容、新功能回归。
   - 修复难度：中等。已有 `web/frontend/src/api` 拆分和 Python 契约测试，但模型/配置/错误码/readiness 的契约仍分散。
   - 优先级：高。继续加功能会让“改一处、炸三处”的概率上升。

### 2. 表象 vs 根本原因

| 表象 | 根本原因 |
|------|----------|
| 用户看到 pending/running 卡住、断线、重复运行防护复杂 | 任务状态既在 SQLite 又在进程内，恢复、取消、重试、幂等的状态机没有成为唯一核心模型 |
| readiness 黄条、修章队列、章节列表口径偶尔需要补契约测试 | 同一章的事实散在 SQLite 记录、workspace 文件、reports、checkpoint、front-end derived state |
| 路由里大量 `except Exception`、fallback、legacy 兼容 | 快速迭代阶段把容错写进业务路径，缺少统一错误边界和观测字段 |
| 前端某些组件 15k-33k bytes，交互越来越难改 | 页面承载了数据获取、派生状态、展示、弹窗、错误提示，拆 composable 后仍有少数容器过胖 |
| 文档写“已完成”，但后续仍不知道下一步做什么 | 已经跨过 MVP，当前问题从功能缺口变为工程治理，路线图需要换焦点 |

### 3. 三个月不处理会变成的技术债

- 长篇/批量生成会从“偶发失败”变成“用户不敢开长跑”：卡住、重复章、半成品章节和恢复策略会消耗大量支持时间。
- 状态漂移会污染后续章节：角色状态、伏笔、钩子、时间线若被错误合并，后面越写越难自动修。
- 兼容层会固化成产品行为：legacy root、YAML mirror、deprecated API 若没有退出策略，新功能必须永远背负旧路径。
- 前端维护成本会快速非线性上涨：大组件继续长大后，局部 UI 改动也需要整页回归。
- 插件系统风险会上升：插件、外部审查、导出 hook 都会触碰状态和文件系统，缺少统一观测/权限/失败边界会拖慢发布。

## 第二层：近期改进方案

按“投入最小、收益最大”排序。

| 优先级 | 改进项 | 改什么 / 怎么改 | 预计工作量 | 验证方式 | 开发节奏 |
|--------|--------|------------------|------------|----------|----------|
| P0 | 建立任务状态机审计表 | 梳理 `pending/running/completed/failed/aborted/queued` 的允许迁移；在 `web/tasks.py` 和 `SQLiteStateStore` 增加 transition helper，记录 `failure_kind/resumable_from/last_heartbeat` | 6-10h | `pytest tests/test_batch_retry_queue.py tests/api/test_api_tasks.py -q`，新增状态迁移单测 | 必须专门处理 |
| P0 | 长任务 heartbeat + stale recovery | 运行中任务每个阶段更新 heartbeat；启动时按 heartbeat 判断 interrupted/stale，而不是粗暴清理所有 running | 6-8h | 人工杀进程后重启，任务显示可恢复/失败原因明确；pytest 覆盖 startup cleanup | 必须专门处理 |
| P1 | 章节事实来源矩阵 | 写一份 `docs/STATE-SOURCES.md`，定义 chapter index、workspace artifacts、reports、SQLite state 的主从关系；把 `/api/chapters` 和 readiness 的口径对齐到该文档 | 3-5h | `pytest tests/test_chapter_index_metadata.py tests/test_workspace_ui_contract.py -q` | 可边做功能边做 |
| P1 | 统一错误边界与异常分类 | 对路由和任务中高频 `except Exception` 改成 `classify_error(exc)`，输出 `code/kind/hint/retryable`；先覆盖 tasks、chapters、models/config | 6-12h | `pytest tests/test_error_codes.py tests/test_security_regressions.py -q`；前端能显示 code + hint | 可分批做 |
| P1 | 配置契约收口 | 把 `pipeline.yaml`、`models.json`、Factory runtime policy、embedding status 的响应字段生成一份前端 TypeScript 类型或契约测试基线 | 4-8h | `npm run test:unit` + `pytest tests/test_pipeline_global_settings.py tests/api/test_api_config.py -q` | 可边做功能边做 |
| P2 | YAML mirror 退出策略 | 对新项目默认 `read_only/off` 做产品决策；只保留显式导出 API；启动日志显示 mirror mode 和 drift count | 4-6h | `pytest tests/test_yaml_mirror.py tests/api/test_api_novel_readiness.py -q` | 需小段专门处理 |
| P2 | 前端大组件拆薄 | 从 `ModelLibrary.vue`、`EmbeddingConfig.vue`、`StateChronicleTab.vue` 中各拆 1 个纯 composable / 子组件，不做视觉改版 | 6-10h | `npm run test:unit && npm run build`，相关页面 Browser 冒烟 | 可边做 UI 功能边做 |
| P2 | 观测面板补“恢复建议” | Monitor/Tasks 页面不仅显示失败，还显示下一步动作：重试、从 checkpoint 续跑、去配置、导出日志 | 4-8h | Playwright/E2E 冒烟；停后端、错配置、失败任务三种场景 | 可边做功能边做 |
| P3 | 插件运行审计 | 插件 hook 记录执行时间、退出码、影响文件、失败类别；前端插件页展示最近失败 | 6-10h | `pytest tests/test_plugin_sandbox.py tests/test_plugin_manager.py -q` | 可延后 |

### 可以边开发新功能边做

- 章节事实来源矩阵，每碰到章节列表、修章、导出、readiness 就同步补一行。
- 配置契约收口，每新增 API 字段就补测试和 TS 类型。
- 前端大组件拆薄，每做一个页面需求时先抽一个无副作用 helper。
- 统一错误分类，可以按路由域渐进改。

### 必须停下来专门处理

- 任务状态机审计表和 heartbeat。它改的是任务核心语义，边做大功能容易引入半套模型。
- YAML mirror 默认策略。如果产品决定切默认行为，需要一次性改文档、迁移提示、测试。
- 长跑恢复验证。必须安排一次 kill/restart/continue 的人工演练。

## 第三层：中长期演进

### 7. 10 倍规模下会先崩哪里

1. **任务执行层先崩**：10 倍章节、10 倍项目、更多自动修章会让内存 task registry、进程内取消标记、单机线程池语义变脆。
2. **状态查询和召回层变慢/变乱**：SQLite 能撑本地单机，但状态表、向量表、章节 artifact 混查会让 readiness、章节列表、连续性 pack 变慢。
3. **审计与重写成本不可控**：连续性、摘要、audit、rewrite 是 LLM 成本和失败率最高的链路，规模上去后需要预算、抽检、降级策略可观测。
4. **前端监控信息密度失控**：任务、日志、告警、章节修复、成本、readiness 如果继续分散，会让用户不知道该点哪里。

### 8. 推荐演进路径

#### 阶段 A：可靠性基线（1-2 周）

- 完成任务状态机、heartbeat、stale recovery。
- 建立长跑演练脚本：启动批量、杀后端、重启、确认任务恢复/失败语义。
- 统一任务失败分类，前端显示明确下一步。

#### 阶段 B：事实来源收敛（1-2 周）

- 明确 SQLite 为主状态，workspace 为章节产物，YAML 为导出/兼容。
- `/api/chapters`、readiness、repair queue、export 共用同一章元数据服务。
- 为每章增加 artifact completeness 检查：plan/final/reports/checkpoint/index 一致性。

#### 阶段 C：契约与配置平台化（1 周）

- 配置 schema 化，后端校验错误能直接映射前端表单字段。
- 前端 API types 与后端 response model 做契约测试。
- deprecated API 标注退出版本和替代路径。

#### 阶段 D：规模策略（2-4 周）

- 引入可插拔任务队列接口，但默认仍用本地 SQLite/asyncio。
- 长篇默认开启向量 readiness、预算阈值、审计抽检策略。
- 对 long/epic/infinite 建立固定 benchmark：100 章 mock chain、10 项目任务切换、导出大书。

#### 阶段 E：扩展生态治理（持续）

- 插件权限、审计、失败隔离做成用户可见。
- 外审/平台反馈进入统一 repair queue，而不是各自开入口。
- 保留本地优先，只有当多人协作或云端托管成为明确目标时再考虑 PostgreSQL / job queue。

### 9. 现在不做但要预留空间

- **Task backend interface**：先抽接口，不马上上 Celery/RQ。预留 `enqueue/cancel/heartbeat/list/recover`。
- **State repository facade**：把章节元数据、状态更新、artifact completeness 放在 service/facade，不让路由直接拼文件。
- **Config schema version**：`pipeline.yaml` 和 `project_meta.json` 预留 `schema_version`，便于迁移。
- **Audit policy plugin point**：审计抽检、平台规则、体裁规则预留策略接口，避免写死在 `AuditPhase`。
- **Vector backend boundary**：SQLite/Chroma/local hash/cloud embedding 保持同一 readiness 和 query 接口。
- **Actor/audit trail**：已有 `X-Novel-Agent-Actor` 概念，后续用于插件、用户操作、自动任务归因。

## 接下来工作 Plan

### Milestone 1：任务可靠性止血

- [x] 写 `docs/TASK-STATE-MACHINE.md`：列出任务状态、允许迁移、恢复语义。
- [x] 为 `SQLiteStateStore` 增加任务 transition helper，不再散落直接 update status。
- [x] 在任务状态/进度更新阶段写 heartbeat。
- [x] 启动 cleanup 记录 `status_reason` / `resumable_from`，为显式恢复提供上下文。
- [x] 补测试：任务生命周期字段、状态迁移日志、heartbeat、重启后任务状态。
- [x] 增强 stale recovery：基于 `last_heartbeat` 区分无心跳、长时间 stale、进程中断。
- [x] 验证：`python -m pytest tests/test_batch_retry_queue.py tests/api/test_api_tasks.py tests/test_checkpoint_rollback.py -q`。

### Milestone 2：状态事实来源收敛

- [x] 写 `docs/STATE-SOURCES.md`：SQLite / workspace / reports / YAML 的主从关系。
- [x] 抽 `chapter_artifact_status` 为章节详情和章节索引的共同依赖。
- [x] 增加 artifact completeness 检查，输出缺失项和修复建议。
- [x] 对 YAML mirror 默认策略做一次产品决策，并更新 `FACTORY-MODE-RUNTIME.md`。
- [x] 验证：`python -m pytest tests/test_chapter_artifact_status.py tests/test_chapter_index_metadata.py tests/test_yaml_mirror.py tests/test_workspace_ui_contract.py -q`。

### Milestone 3：契约与错误边界

- [x] 统计高频 `except Exception`，先处理 tasks、chapters、config、model library 四个域。
- [x] 扩展 `novel_agent/errors/`：补 `retryable`、`user_action`、`resumable_from`。
- [x] 前端统一错误展示 helper，Monitor/Tasks/Config 复用。
- [x] 配置 API response 增加 schema/version 字段，并补前端类型或契约测试。
- [x] 验证：`python -m pytest tests/test_error_codes.py tests/api/test_api_config.py tests/test_security_regressions.py -q`，`cd web/frontend && npm run test:unit && npm run build`。

### Milestone 4：前端复杂度削峰

- [x] 为 `ModelLibrary.vue` 抽模型表单/预设转换 helper（预设卡片当前为隐藏 UI，暂不拆子组件）。
- [x] 为 `EmbeddingConfig.vue` 抽 readiness/fix-steps 纯逻辑。
- [x] 为 `StateChronicleTab.vue` 抽 timeline grouping/filter helper。
- [x] 每次只拆一个页面，保持视觉不改。
- [x] 验证：`cd web/frontend && npm run test:unit && npm run build`。
- [ ] 相关路由 Browser 冒烟：已尝试；in-app Browser 无法完成本地 token `prompt()` / `localStorage` 注入，需在已登录浏览器或 Electron 环境补跑。

## 执行建议

- 第一周只做 Milestone 1，不夹带新功能。
- 第二周做 Milestone 2 + 小范围错误分类。
- 之后每个新功能 PR 必须带一项契约或大组件削峰，保持“功能前进”和“债务下降”同时发生。
- 每周固定跑一次：后端 pytest、前端 unit/build、bundle check、一次 mock 长跑恢复演练。

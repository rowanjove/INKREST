# 改进路线图 2026 Q2

与 [PLAN-全书链路与人机协同.md](./PLAN-全书链路与人机协同.md)（产品车道）互补；本文跟踪工程与可运维项。

## 已完成（2026-06 全量改进）

- [x] Git 基线 + CONTRIBUTING 本地验证清单
- [x] 连写 UX：记住章数、本轮进度、分阶段取消说明
- [x] 长篇向量黄条 + audit_profile 设置展示
- [x] 修章队列命名 + 山山三步排障 + `GET /api/novel/autopilot-rounds`
- [x] FirstBookGuide 按体量分轨、任务失败聚合条
- [x] 示例插件 `plugins/examples/hello_guard.py`、`txt_export_hook.py`
- [x] 书库卡片待处理角标（`pending_alert_count` + pipeline alerts 口径）
- [x] 连写弹窗按日常模型 `blended_price_per_1k_cny` 估费
- [x] `autopilot_rounds.jsonl` 写入 `tokens_used`
- [x] `test_autopilot_one_round_mock.py` 冒烟

## 已完成（2026-06）

- [x] 结构化错误码 `novel_agent/errors/`
- [x] 任务失败 `failure_kind` / `failure_hint`（`web/task_failures.py`）
- [x] `/api/system/readiness` 系统自检
- [x] WebSocket 首帧 `auth`（浏览器无法设 Header）
- [x] 前端 WS 任务进度 + 监控失败条（`failure_hint` / `code` 展示）
- [x] 设置页 `SystemReadinessPanel` + 侧栏运行状态合并 `/api/system/readiness`
- [x] 前端 `utils/errorCodes.ts` 与后端错误码对齐
- [x] CI：`novel-agent-full.yml`、可选 `novel-agent-llm-nightly.yml`
- [x] `tests/smoke/test_llm_one_chapter.py`（需环境变量）
- [x] `scripts/chaos_long_run.py`、`scripts/verify_bundle_manifest.py`
- [x] autopilot `workspace/autopilot_rounds.jsonl`
- [x] `.gitignore` 排除 `scratch/`、`dist-portable/`

## 待办（Batch2 · 一次搞完）

详见 [PLAN-UPGRADE-2026Q2-BATCH2.md](./PLAN-UPGRADE-2026Q2-BATCH2.md)（15 工作包：QA×3、UX×4、车道 A×3、车道 B×3、扩展×2）。

- [x] QA-1 E2E 进 CI
- [x] QA-2 Vitest（batchRunForm / tokenCostEstimate）
- [x] QA-3 chaos workflow_dispatch
- [x] UX-1 开书清单进度条
- [x] UX-2 三处空状态统一
- [x] UX-3 Electron 断线 toast
- [x] UX-4 书库角标 → 修章维护深链
- [x] A-1 真实费用看板
- [x] A-2 体量门禁设置可感知
- [x] A-3 长篇向量可修复流程
- [x] B-1 修章队列筛选（门禁/跳过/外审）
- [x] B-2 章节列表「只重跑门禁」
- [x] B-3 外审续跑策略 UI
- [x] E-1 插件 examples README + 入口
- [x] E-2 打包版本与 manifest 发布清单
- [x] E-3 连载 Tab 弱耦合增强

## 待办（按优先级 · Batch1 已完成）

### P1

- [x] `orchestrator.py` 续拆：`orchestrator_novel_batch.py` + `orchestrator_types.py`（主文件约 490 行）
- [x] `phases/audit.py` 拆分：`audit_matching.py`、`audit_rewrite.py`（Mixin）
- [x] 设置页展示 `/api/system/readiness` 检查结果

### P2

- [x] Electron 单源：`scripts/sync_electron_canonical.ps1`（canonical：`web/frontend/electron`）
- [x] 插件子进程沙箱（hook 隔离，`runtime.plugin_sandbox`）
- [x] `ProjectSession` 轻量 DI（`web/deps.py`，`/api/system/readiness` 已接入）

### P3

- [x] 连写弹窗展示 token 费用预估（粗估 1.2 万 tokens/章）
- [x] Playwright 脚手架（`npm run test:e2e`，默认 skip，设 `E2E_RUN=1` 执行）

## 验收指标

| 指标 | 目标 |
|------|------|
| PR smoke | &lt;5min 绿 |
| 任务失败可分类 | 监控页显示 code + hint |
| 打包清单 | `verify_bundle_manifest.py` 通过 |
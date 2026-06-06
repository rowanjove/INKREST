# 改进路线图 2026 Q2

与 [PLAN-全书链路与人机协同.md](./PLAN-全书链路与人机协同.md)（产品车道）互补；本文跟踪工程与可运维项。

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

## 待办（按优先级）

### P1

- [x] `orchestrator.py` 续拆：`orchestrator_novel_batch.py` + `orchestrator_types.py`（主文件约 490 行）
- [x] `phases/audit.py` 拆分：`audit_matching.py`、`audit_rewrite.py`（Mixin）
- [x] 设置页展示 `/api/system/readiness` 检查结果

### P2

- [x] Electron 单源：`scripts/sync_electron_canonical.ps1`（canonical：`web/frontend/electron`）
- [ ] 插件子进程沙箱（hook 隔离）
- [x] `ProjectSession` 轻量 DI（`web/deps.py`，`/api/system/readiness` 已接入）

### P3

- [x] 连写弹窗展示 token 费用预估（粗估 1.2 万 tokens/章）
- [ ] 全量 E2E Playwright（可选）

## 验收指标

| 指标 | 目标 |
|------|------|
| PR smoke | &lt;5min 绿 |
| 任务失败可分类 | 监控页显示 code + hint |
| 打包清单 | `verify_bundle_manifest.py` 通过 |
# 栖墨 · 技术顾问行动指南（2026 Q2）

> 三层诊断的持久化摘要；与 [PLAN-全书链路与人机协同.md](./PLAN-全书链路与人机协同.md)（产品车道）互补。

## 北极星

让 **工厂模式** 与 **体量档位** 从配置文案变成可感知的运行时行为；收敛 WIP 为可发布版本。

## Sprint 进度

| Sprint | 内容 | 状态 |
|--------|------|------|
| 0 | 基线验证、WIP commit、VERSION/validate_release | ✅ |
| 1 | `factory_policy` → `runtime_policy` / 门禁 / 续跑 | ✅ |
| 2 | `factory_summaries` 拆分、YAML 镜像 flag、向量 readiness override | ✅ |
| 3 | 前端 `api/` 域拆分、`useTaskProgress`、`ProjectSessionDep` | ✅ |
| 文档 | `PROJECT.md`、`FACTORY-MODE-RUNTIME.md`、本文件 | ✅ |

## 近期改进（按 ROI 排序）

1. **WIP 收敛发布** — 全量 pytest + vitest + bundle check ✅
2. **Factory 引擎闭环** — `FACTORY-MODE-RUNTIME.md` + Dashboard 工厂面板 + `test_factory_mode_policy` / `test_factory_dashboard` ✅
3. **文档/契约同步** — UI 契约测试镜像关键前端约定 ✅
4. **YAML 止血** — `yaml_mirror_mode`（`read_only`/`off`）+ 导出 API + 启动漂移日志 ✅
5. **向量长篇** — `vector_readiness` + `/api/novel/readiness` 与连写弹窗对齐 ✅
6. **请求级上下文** — `ProjectSession` + 大纲/连写写路由 `RequireProjectDep` ✅
7. **前端域拆分** — `api/client|factory|chapters`、`useTaskProgress` ✅

## 中长期（刻意分阶段）

| 阶段 | 目标 | 状态 | 不做 |
|------|------|------|------|
| 2 数据 | YAML `read_only` + 导出 API；章节 index `gate_status`/`has_final` | ✅ | 迁 PostgreSQL |
| 3 召回 | long/epic 默认 ChromaDB + readiness 暴露 backend | ✅ | 云向量服务 |
| 4 执行 | 项目级 TaskManager 注册表 + `max_concurrent_chapters` | ✅ | 盲目上 Celery |
| 5 平台 | 全路由 `ProjectSession`（≥95%）+ `X-Novel-Agent-Actor` | ✅ | 微服务拆分 |

## 每周自检

1. `pytest` + `vitest` + `check:bundle` 全绿？
2. 本周 `factory_mode` / `scale_profile` 改动是否有测试？
3. 是否新增无 WS 的 `setInterval` 轮询？
4. `PROJECT.md` 数字是否与仓库一致？
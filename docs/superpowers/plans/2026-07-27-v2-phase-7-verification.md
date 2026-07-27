# V2 Phase 7 验收记录：最终清理、旧数据重置与交付

> 日期：2026-07-27
> 分支：`codex/v2-refactor`
> 结果：通过

## 交付结论

V2 的最后收口已完成。项目删除会先停止并释放项目级后台对象；误导性的“清空数据库”页面已替换为先备份、再重置的项目维护页；旧根目录不会再在启动时被猜测成项目；确认无调用方的前端组件、工具、store、Electron 客户端和 API 包装已删除；运行日志会在应用退出时关闭；旧项目已生成受控备份并重置到 schema V2；Windows 目录包、真实 renderer、五种导出和单实例行为均通过验证。

Phase 7 相对计划起点共修改 49 个文件，新增 1,939 行、删除 3,285 行，净减少 1,346 行。删除量包括 1,850 行无入口前端组件/工具和 205 行无调用方 API 包装。所有小说生成、审核、重写、批量运行和模型调用均未触发。

## 社区方案与死代码审计

- Vue/TypeScript 使用 [Knip](https://github.com/webpro-nl/knip) 6.29.0，并将 `npm run audit:dead-code` 固化到项目中；文件、依赖、未声明依赖和无法解析导入均为 0。
- Python 使用 [Vulture](https://github.com/jendrikseipp/vulture) 的 100% 置信度审计，并排除构建和生成目录；没有确认可删除的 Python 候选。
- 工具结果没有直接用于批量删除。每个候选均用 `rg`、Vue 路由、Electron 入口、CLI、插件边界和测试反向复核。
- Electron 主进程、更新器、宠物 IPC 和安全模块存在多入口特性，作为明确审计入口保留；抽象方法参数和可选依赖探测属于 Vulture 误报边界。
- `@element-plus/icons-vue` 2.3.2 已改为直接生产依赖，不再依赖传递安装。

确认删除的旧表面包括 `AiBubbleMenu`、`AssetSidebar`、`CharacterCard`、`DashboardStats`、`DataManager`、`ProxyConfig`、`RecentChapterDialog`、`RichEditor`、`SystemReadinessPanel`、`PetStatusCard`、旧配置 store/barrel/工具，以及未使用的 Electron `llm-client`。仍在使用的 `OutlineEditorLegacy` 仅改名为 `OutlineEditor`，功能完整保留。

## 数据与生命周期修复

- `TaskManager.shutdown()`、`ProjectTaskRegistry.drop()` 和 `release_project()` 形成完整释放链；删除项目时先终止轮询和后台任务，再删除经过注册、路径边界和符号链接校验的精确项目目录。
- 设置页新增 `ProjectDataMaintenance`：仅备份要求输入 `BACKUP <project_id>`；备份并重置要求输入 `RESET V2 <project_id>`。界面明确展示保留项、清理项、备份位置和失败原因，重置后重新 hydrate。
- 启动过程不再把仓库根级 `data/state/config/workspace` 猜测为默认项目，只加载注册表中的活动项目。
- `shutdown_logging()` 会关闭应用创建的日志 handler，修复了 Windows 临时目录在应用退出后仍被日志文件占用的问题。
- 新增 `scripts/cleanup_v2_runtime.py`。默认仅预览，执行必须提供精确确认词 `CLEAN V2 RUNTIME`；它只接受数据卷直接子目录、拒绝符号链接，并且只删除未注册项目和显式根级运行目录。

## 桌面旧项目备份与重置

所有备份都排除了密钥、日志和插件，拒绝外部符号链接，并完成 ZIP CRC 与 SHA-256 校验。三个桌面项目均无活动任务，重置后为 schema V2。

| 项目 | 备份 | 文件数 / 大小 | SHA-256 |
| --- | --- | ---: | --- |
| `6cbc2f72` 枪线之上 | `C:\Users\26241\AppData\Roaming\novel-agent-desktop\backups\v2-reset\6cbc2f72-20260727T110833722682Z.zip` | 367 / 1,011,966 bytes | `ca351754e3c136c7cdb2e684257b3ab50666c5ddbe7cf7bea8dfd5aa6d7a3feb` |
| `451d8f6f` 《心之所向》 | `C:\Users\26241\AppData\Roaming\novel-agent-desktop\backups\v2-reset\451d8f6f-20260727T110835120543Z.zip` | 109 / 472,121 bytes | `b6d0184984b23ea214f60d3ae25fd980e9cf05ca4e13c6f4ed7e1f67efd70c35` |
| `59429c36` 死局之外 | `C:\Users\26241\AppData\Roaming\novel-agent-desktop\backups\v2-reset\59429c36-20260727T110835766317Z.zip` | 345 / 1,410,460 bytes | `dc76e457b9e948195bcf37b4f01cdef2d64aab9f7ac556c5485583a5003f5898` |

仓库根级旧运行时也在清理前完成受控备份：

| 数据卷 | 备份 | 大小 | SHA-256 |
| --- | --- | ---: | --- |
| 主仓库 | `F:\AI\vibecoding\小说生成agent\backups\legacy-root\root-runtime-20260727T190947136.zip` | 121,043 bytes / 273 entries | `559ad8613a0bbd2fdfa287785218ee8252b570af8cccbd546d0d3b2620027b1a` |
| V2 worktree | `F:\AI\vibecoding\小说生成agent\.worktrees\v2-refactor\backups\legacy-root\root-runtime-20260727T190951611.zip` | 293 bytes / 2 entries | `1339759dda83c1a556cc640a0a84a5b24ef0f55f4cd3a80c1619c0d762d60c92` |
| 桌面数据卷 | `C:\Users\26241\AppData\Roaming\novel-agent-desktop\backups\legacy-root\root-runtime-20260727T190951665.zip` | 5,481 bytes / 3 entries | `7909d6dd9b4ae174db49438cb49d8db075d2f8d9246909156572964c25c36332` |

初次清理移除了主仓库 158 个、V2 worktree 72 个、桌面数据卷 6 个未注册测试/孤儿项目。最终回归后又移除了 V2 worktree 的 3 个已注册 E2E 测试项目和 11 个测试孤儿目录；这些测试数据不可恢复，但可通过重跑 E2E 重新生成。最终三处数据卷复扫结果均为 0 个孤儿项目、0 个根级旧运行目录；桌面三个真实项目和全部备份保留。

## 最终自动化验收

| 门禁 | 结果 |
| --- | --- |
| `npm ci` | 通过 |
| `npm run audit:dead-code` | 0 个文件/依赖/未声明依赖/无法解析导入问题 |
| `npm run test:unit` | 34 个文件，173 个测试通过 |
| `npm run test:electron` | 13 个测试通过 |
| `npm run build` + `npm run check:bundle` | 通过；48 个 JS chunk，1,810,281 bytes |
| `npm audit --omit=dev --audit-level=high` | 0 vulnerabilities |
| 全依赖 `npm audit` | 17 条开发工具链告警：1 low、16 high；生产依赖不受影响 |
| Ruff | 全量通过 |
| `py -3.12 -m pytest tests/ --ignore=tests/smoke -q --tb=short` | 846 passed，10 subtests passed，2 条 Pillow 未来弃用提醒 |
| API 性能基线 | 通过 |
| `py -3.12 -m pip check` | No broken requirements |
| `E2E_RUN=1 npm run test:e2e` | 34 passed |
| `py -3.12 scripts/validate_release.py` | 通过 |
| bundle manifest 验证 | 无开发目录、密钥、本地配置、数据库、日志或运行时数据 |

临时 Python 3.12 环境从 `requirements.txt` 与 `requirements-build.txt` 干净安装，导入、健康检查和五格式导出全部通过：TXT 121 bytes、Markdown 55 bytes、DOCX 36,730 bytes、EPUB 2,566 bytes、PDF 2,991 bytes。临时环境随后精确删除。

## Windows 打包实测

- Python 3.12 / PyInstaller 6.21 sidecar 重新构建通过。
- `electron-builder --win --dir` 重新生成 `win-unpacked` 通过。
- 真实 Electron renderer 打开 `/publishing?tab=export&chapter=001`，5 种格式均可用，TXT 下载返回 200、413 bytes，正文来自 SQLite，页面无横向溢出。
- 包内后端五格式复核通过：TXT 222 bytes、Markdown 160 bytes、DOCX 36,868 bytes、EPUB 2,719 bytes、PDF 3,136 bytes。TXT/Markdown 按 Unicode 码点验证“林越”，DOCX/EPUB 通过 ZIP CRC，PDF 通过 `%PDF-` 签名。
- 单实例实测通过：第二实例以退出码 0 主动退出，首实例及其 sidecar 持续运行；测试结束后包进程数量为 0。
- renderer 截图保存在忽略构建目录 `web/frontend/dist-desktop/win-unpacked/smoke-results/packaged-publishing.png`，未进入 Git。

## 最终状态

- `git diff --check` 通过。
- 提交内容不包含 `.env`、API Key、用户配置、项目数据、日志、数据库或打包产物。
- 运行态清理后二次扫描为零残留，且没有 `栖墨` 或 `novel-agent-backend` 进程。
- V2 分支源代码与文档均已提交，达到 Phase 7 完成标准。

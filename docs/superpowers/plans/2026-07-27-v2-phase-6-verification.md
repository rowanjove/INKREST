# V2 Phase 6 验收记录：发布、设置、扩展权限与桌面安全

> 日期：2026-07-27
> 分支：`codex/v2-refactor`
> 结果：通过

## 交付范围

- SQLite `documents` 成为预览、试读与五种导出的唯一正文来源。
- `/publishing` 统一成书预览、平台与反馈、黄金三章、发布预检和导出交付。
- 设置页改为六个用户任务组，高级配置与常用表单分离。
- 扩展中心实施内容摘要、权限枚举、显式信任、变更后重新授权和运行时启用检查。
- Electron 完成全局 sandbox、session 权限拒绝、导航/外链/IPC 边界、单实例和 Python 子进程幂等生命周期。
- Windows 包内包含 TXT、Markdown、DOCX、EPUB 3、PDF 所需依赖和前端资源。

## 自动化验收

| 门禁 | 结果 |
| --- | --- |
| `py -3.12 -m pytest tests/ --ignore=tests/smoke -q --tb=short` | 837 passed，10 subtests passed，2 个 Pillow 未来弃用警告 |
| `npm run test:unit` | 172 passed |
| `npm run test:electron` | 13 passed |
| 显式 Playwright（稿件、扩展、发布） | 7 passed |
| `npm run build` | 通过 |
| `npm run check:bundle` | 48 个 JS chunk，共 1,808,026 bytes，预算内 |
| `npm audit --omit=dev --audit-level=high` | 0 vulnerabilities |
| `py -3.12 -m pip check` | No broken requirements |
| `py -3.12 scripts/validate_release.py --check-bundle` | 通过 |
| `py -3.12 scripts/verify_bundle_manifest.py .../win-unpacked` | 无开发目录、密钥、本地配置、数据库、日志或运行时数据 |

## 打包链路验收

初次验证发现旧 `build:backend` 会使用系统默认 Python 3.8，虽然 PyInstaller 返回 0，但无法收集采用 Python 3.11+ 类型语法的导出模块。这是发布阻断问题，已修复为：

- 构建器只选择项目支持的 Python 3.11 或 3.12；
- 在冻结前验证 PyInstaller、FastAPI、Pydantic、DOCX、ReportLab 和 `novel_agent.exporters` 可导入；
- PyInstaller 版本固定为 6.21.0；
- Python 3.12 构建工作目录与旧版本缓存隔离；
- DOCX、ReportLab 和项目导出模块显式收集；
- Windows 目录包使用完整描述和作者元数据。

最终产物：

- Python 3.12.10 / PyInstaller 6.21.0 onedir sidecar 构建通过；
- `electron-builder --win --dir` 构建 `win-unpacked` 通过；
- 包内后端启动、健康检查和内置前端根页面均返回 200；
- 第二实例启动后仍只有 1 个 Electron 根进程和 1 个 Python sidecar；
- 停止验收后，属于打包目录的进程数为 0。

## 包内五格式实测

使用打包后的 `novel-agent-backend.exe`、独立测试项目和 SQLite 文稿，通过真实 HTTP 下载并回读：

| 格式 | 大小 | 校验 |
| --- | ---: | --- |
| TXT | 222 bytes | UTF-8 正文包含 SQLite 文稿 |
| Markdown | 169 bytes | UTF-8 正文包含 SQLite 文稿 |
| DOCX | 36,882 bytes | ZIP/OOXML 文件头有效 |
| EPUB 3 | 2,737 bytes | ZIP/EPUB 文件头有效 |
| PDF | 3,180 bytes | `%PDF-` 文件头有效 |

随后连接真实打包 Electron renderer：

- 打开 `app.asar` 提供的 `/publishing?tab=preview&chapter=001`；
- 识别到 5 种可用导出格式；
- 页面无横向溢出，等待加载遮罩消失后截图；
- 通过 UI 的“检查并下载 → 确认下载”发起 TXT 导出；
- 响应 200、413 bytes，内容包含 SQLite 正文“林越”；
- 烟测自动终止夹具的假任务并删除自己创建的测试项目；
- 没有触发生成、审核、重写或任何模型请求。

## 人工视觉验收

- 发布中心：1440×900 明亮主题与 1100×720 暗色主题通过，目录、正文和工具条无横向溢出。
- 设置：六个任务组和三个高级区通过，常用配置与源码编辑边界清楚。
- 扩展中心：未信任扩展、风险标签、权限列表、SHA-256 摘要与确认禁用态通过。
- 打包 Electron 发布中心最终态截图通过，中文正文、目录、成书版心和导航正常。

## 结论

Phase 6 的功能、权限、安全、依赖和 Windows 打包验收均完成。剩余工作进入 Phase 7：执行已授权的数据重置与清理、删除最终死代码/兼容残留、补齐总文档和发布前全量复核。

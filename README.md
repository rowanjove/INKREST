# 栖墨 · INKREST — 长篇小说创作与生产工作台

[简体中文](README.md) | [English](README.en.md)

栖墨是一款本地优先的小说创作工作台，将大纲、章节编辑、多 Agent 辅助写作、连续性检查和多格式导出放在同一项目中。作者可以手动写作，也可以按需运行单章或批量生成，并在质量检查、修订历史和任务日志中查看结果。

[下载 Windows v2.0.2](https://github.com/rowanjove/INKREST/releases/tag/v2.0.2) · [更新记录](CHANGELOG.md) · [问题反馈](https://github.com/rowanjove/INKREST/issues)

作品与项目状态保存在本地。**调用远程模型时，所选上下文会发送到配置的模型服务，并可能产生费用**；本地优先不代表模型推理一定离线。

![栖墨项目概览与生产状态](docs/images/readme-overview.png)

## 安装与首次使用

Windows 用户可从 Release 下载 `Setup.2.0.2.exe` 安装包，或 `2.0.2.exe` 便携版。

启动后创建作品、配置模型服务，再选择手动编辑或辅助生成。开始真实模型任务前，核对服务地址、模型、密钥和费用设置。普通页面浏览不会自动发起写作模型调用；生成、重写、审校和批量任务由用户明确发起。

下方源码步骤适用于开发者，不是使用 Windows 发布包的前置要求。

## 工作区与生成流程

| 工作区 | 用途 |
| --- | --- |
| 开书与策划 | 管理大纲、卷纲、人物关系、世界设定、时间线与素材 |
| 正文编辑 | 富文本编辑、自动保存、修订历史、上下文查看和按需改写 |
| 章节生产 | 策划、场景写作、拼接、文风编辑、审校与状态更新 |
| 质量检查 | 连续性、篇幅、敏感词及重复／模板化表达检测 |
| 长篇记忆 | SQLite 项目状态、章节摘要、检查点和可选向量召回 |
| 发布导出 | TXT、Markdown、DOCX、EPUB 3 和 PDF |
| 扩展 | 项目隔离、备份、插件权限与项目级作用域 |

章节流水线按计划组织写作、编辑和检查，并支持批量生产、断点续跑、失败重试与连续失败暂停。正文和任务以项目级 SQLite 为数据源；兼容文件与章节产物不应覆盖较新的数据库记录。

![栖墨正文工作区](docs/images/readme-writer.png)

## 文风与连续性

生成前可配置文风、禁用表达和写作约束；生成后由文风编辑、本地规则与模型审校发现问题，再进行定向修正或人工改稿。检查结果用于辅助编辑，不是作品质量或事实正确性的保证，也不承诺通过第三方 AI 检测。

长篇任务可召回人物、设定、事件、伏笔及历史片段。向量召回是可选能力，需要相应模型与索引就绪。问题导致质量门禁阻断时，应检查报告再决定修章、重跑或继续。

项目提供新手自动、作者协作、平台审校、长篇稳定和工作室等运行模式。它们调整生成与检查策略，不代替作者的最终判断。

## 山山助手

山山常驻 Electron 桌面端，读取作品、任务和日志状态，解释暂停原因，提供页面导航、模型连通性测试、单章重试、自动修章与门禁重跑入口。对话模型可单独配置。

涉及模型调用或正文变更的操作需要用户触发和相应确认。助手不应擅自改大纲、删除项目或绕过确认续跑全书。

![栖墨书库](docs/images/readme-library.png)

截图使用内置示例书，不包含私人作品或密钥。

## 从源码启动

需要 Python **3.11 或 3.12**、Node.js **>=22.12.0**。桌面打包目标为 Windows 10/11。

在 Windows PowerShell 中：

```powershell
git clone https://github.com/rowanjove/INKREST.git
cd INKREST
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item config/pipeline.yaml.example config/pipeline.yaml
cd web/frontend
npm ci
npm run build
cd ../..
./.venv/Scripts/python.exe main.py serve --no-browser
```

访问 `http://127.0.0.1:8000`。源码启动需要先构建前端；后端从 `web/frontend/dist` 提供页面。修改前端后应重新构建，或使用开发流程。

按需在本地 `config/pipeline.yaml` 或 `config/models.json` 配置模型。它们和 `.env` 已被 Git 忽略，不要强制提交。虚拟环境 `.venv/` 也不应提交；可将它加入本地 `.git/info/exclude`。

### 不消耗模型额度的命令行示例

在仓库根目录使用静态模型干跑：

```powershell
./.venv/Scripts/python.exe main.py run-chapter --chapter-id 001 --goal "主角雨夜回到出租屋，并遭遇第一次异常。" --dry-run
```

干跑仍可创建本地产物，不等于只读操作。章节产物位于当前项目的 `workspace/chapters/`。

### Windows 桌面构建

打包脚本会探测 Python 3.12／3.11 环境；为它安装运行和构建依赖：

```powershell
py -3.12 -m pip install -r requirements.txt -r requirements-build.txt
cd web/frontend
npm run electron:build
```

产物位于 `web/frontend/dist-desktop/`。如只需要目录版，可先运行 `npm run build:backend`，再运行 `npm run electron:pack`；目录版程序为 `win-unpacked/栖墨.exe`。完整验收见 [贡献与本地验证](CONTRIBUTING.md)。

## 验证

后端，在仓库根目录：

```powershell
./.venv/Scripts/python.exe -m pip install pytest pytest-asyncio
./.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/smoke -q --tb=short
```

前端：

```powershell
cd web/frontend
npm run test:unit
npm run test:electron
npm run build
npm run check:bundle
```

`check:bundle` 使用 PATH 中的 `python`，请确保它指向兼容的 Python 环境。更完整的 lint、性能、E2E 和打包冒烟步骤见贡献指南。真实模型测试可能消耗额度，不应无确认地运行。

## 数据、密钥与插件

- `projects/`、`workspace/`、`data/`、`state/`、`logs/` 和 `backups/` 默认不提交。
- 服务默认监听 `127.0.0.1`；远程监听需要显式启用并配置访问令牌。
- 项目备份与 V2 重置使用带项目编号的确认词；重置前生成可校验备份。
- API、日志与备份流程会隔离或脱敏密钥；分享诊断前仍应检查内容。
- 插件权限需要基于清单哈希授权；安装插件不代表自动信任或允许全部操作。

## 技术与文档

后端使用 Python、FastAPI、Pydantic 和 SQLite；前端使用 Vue 3、TypeScript、Pinia、Vite、Element Plus 与 Tiptap；桌面端使用 Electron 和 PyInstaller。测试包括 pytest、Vitest 与 Playwright。

[架构](docs/ARCHITECTURE.md) · [贡献指南](CONTRIBUTING.md) · [插件作者指南](docs/plugins/PLUGIN_AUTHOR.md) · [Agent 集成](docs/AGENT-INTEGRATION.md) · [数据备份与重置](docs/V2-DATA-RESET.md) · [远程部署安全](docs/remote-deployment-security.md)

## 许可

采用 [Apache License 2.0](LICENSE)，版权与署名见 [NOTICE](NOTICE)。

# 栖墨

栖墨是一套本地优先的长篇小说创作、生产与发布工作台。它把策划、写作、审校、状态追踪和多格式导出放进同一个桌面应用，并用多智能体流水线协助完成长篇内容生产。

> 当前为个人开发项目，优先支持 Windows 桌面端。页面浏览和状态读取不会自动调用模型；续写、批量运行、重写与审校都需要用户主动确认。

![栖墨项目概览](docs/images/readme-overview.png)

## 主要能力

- **书库与项目隔离**：创建、导入、切换、置顶和维护多本作品，每本书使用独立的数据与任务作用域。
- **策划中心**：管理大纲、卷纲、角色关系、世界设定、时间线与故事素材。
- **正文中心**：提供章节目录、富文本编辑、自动保存、修订历史、上下文和人工确认后的智能建议。
- **生产中心**：统一查看生成任务、审校修复、费用、运行日志和阻塞原因。
- **发布中心**：从正文真源预览内容，并导出纯文本、Markdown、DOCX、EPUB 与 PDF。
- **本地优先**：正文、任务和叙事状态保存在项目级 SQLite 数据库中，模型密钥与用户作品不进入代码仓库。
- **桌面体验**：Vue 3 前端与 Electron 桌面壳，内置单实例保护、后端伴随进程和山山驻场助手。
- **扩展系统**：第一方插件清单、权限授予、安装校验和项目级插件作用域。

## 界面预览

### 正文工作区

![栖墨正文工作区](docs/images/readme-writer.png)

### 书库

![栖墨书库](docs/images/readme-library.png)

截图使用仓库内置示例书，不包含私人作品或模型密钥。

## 技术组成

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11 / 3.12、FastAPI、Pydantic、SQLite |
| 前端 | Vue 3、TypeScript、Pinia、Vite、Element Plus |
| 编辑与图形 | Tiptap、Vue Flow、TanStack Virtual |
| 桌面端 | Electron、electron-builder、PyInstaller |
| 测试 | pytest、Vitest、Playwright |

正文、任务和叙事状态以 SQLite 为真源；工作区中的兼容文件与章节产物不会反向覆盖更新的数据。项目默认只监听 `127.0.0.1`，远程监听必须显式启用访问令牌。

## 快速开始

### 环境要求

- Python 3.11 或 3.12
- Node.js 22 或满足前端依赖要求的更新版本
- Windows 10 / 11（桌面打包与当前交付形态）

### 安装依赖

```powershell
py -3.12 -m pip install -r requirements.txt

cd web\frontend
npm ci
cd ..\..
```

### 准备本地配置

```powershell
Copy-Item config\pipeline.yaml.example config\pipeline.yaml
```

在 `config/pipeline.yaml` 或 `config/models.json` 中填写模型地址、模型名与密钥。这两个文件以及 `.env` 已被忽略，不应提交。

### 启动网页工作台

```powershell
python main.py serve --no-browser
```

然后访问 `http://127.0.0.1:8000`。

### 构建桌面端

```powershell
cd web\frontend
npm run electron:pack
```

构建完成后运行：

```text
web\frontend\dist-desktop\win-unpacked\栖墨.exe
```

完整安装包构建使用 `npm run electron:build`。

## 命令行示例

下面的干跑模式使用静态模型，不消耗模型额度：

```powershell
py -3.12 main.py run-chapter `
  --chapter-id 001 `
  --goal "主角雨夜回到出租屋，并遭遇第一次异常。" `
  --dry-run
```

章节产物位于当前项目的 `workspace/chapters/`。不要在未经确认的情况下运行连续生成、批量章节或真实模型任务。

## 验证

后端：

```powershell
python -m pytest tests/ --ignore=tests/smoke -q --tb=short
```

前端：

```powershell
cd web\frontend
npm run test:unit
npm run test:electron
npm run build
npm run check:bundle
```

更完整的提交、性能、端到端和桌面打包门禁见 [贡献与本地验证](CONTRIBUTING.md)。

## 数据与安全

- `.env`、`config/pipeline.yaml`、`config/models.json` 不进入版本控制。
- `projects/`、`workspace/`、`data/`、`state/`、`logs/`、`backups/` 与构建产物默认忽略。
- 项目备份与 V2 重置都要求输入带项目编号的精确确认词，并在重置前生成可校验备份。
- API 返回、日志与备份流程会对密钥进行隔离或脱敏。
- 插件启用前需要基于清单哈希授予权限。

详见 [V2 数据备份与重置](docs/V2-DATA-RESET.md) 和 [远程部署安全](docs/remote-deployment-security.md)。

## 项目文档

- [架构与代码结构](docs/ARCHITECTURE.md)
- [贡献与本地验证](CONTRIBUTING.md)
- [插件作者指南](docs/plugins/PLUGIN_AUTHOR.md)
- [Agent 集成](docs/AGENT-INTEGRATION.md)
- [V2 数据备份与重置](docs/V2-DATA-RESET.md)
- [远程部署安全](docs/remote-deployment-security.md)

## 当前授权状态

仓库目前没有附加开源许可证，保留所有权利。私有开发不受影响；如果将来公开并希望他人使用、修改或分发代码，应先选择并加入合适的开源许可证。

# 栖墨 · INKREST — 多 Agent 长篇写作

本地优先的智能长篇流水线：章节规划 → 写作 → 审校 → 状态同步，配套 Vue 工作台与 Electron 桌面端（栖墨）。

## 当前能力

- Planner 生成章节计划和场景卡。
- Context Builder 生成每个场景的最小上下文包。
- Writer 写单场景；Length Fix / Stitch / Style / Auditor 等后续阶段。
- 自动加载 `prompts/*.md`；审校 JSON 校验；敏感词扫描。
- `state_update` 合并到 `state/*.yaml` + SQLite 镜像 `data/novel.sqlite`。
- 多场景并行、向量召回、插件扩展、山山驻场助手、全书连写与章节维护。

## 快速开始

### 1. 依赖与配置

```powershell
pip install -r requirements.txt
copy config\pipeline.yaml.example config\pipeline.yaml
```

在 `config/pipeline.yaml` 或 `config/models.json` 填入模型 API Key（二者已在 `.gitignore`，勿提交）。

### 2. 启动 Web 后台

```powershell
# 推荐
python main.py serve --no-browser

# 或双击
start.bat
```

浏览器打开 http://127.0.0.1:8000 。桌面端请使用下方 **栖墨 Electron** 打包产物（会自动拉起同一后台）。

### 3. 桌面端（推荐交付形态）

```powershell
cd web\frontend
npm ci
npm run electron:pack
```

运行：`web\frontend\dist-desktop\win-unpacked\栖墨.exe`

若已构建过 PyInstaller 后端，仅更新前端时可：

```powershell
cd web\frontend
npm run build
npm run sync:python-runtime
npx electron-builder --win --dir
```

## 运行测试

```powershell
# 后端（与 CI 一致）
python -m pytest tests/ --ignore=tests/smoke -q

# 前端
cd web\frontend
npm run test:unit
npm run build
npm run check:bundle
```

可选导出/向量相关测试依赖：`pip install -r requirements-extras.txt`

推送前完整清单见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## CLI（无 Web UI）

```powershell
# 干跑一章（StaticLLM，不耗 API）
python main.py run-chapter --chapter-id 001 --goal "主角雨夜回到出租屋，并遭遇第一次异常。" --dry-run

# 等价旧入口（会提示迁移到 cli.py / main.py）
python cli.py run-chapter --chapter-id 001 --goal "..." --dry-run
```

章节产出目录：`workspace/chapters/chapter_001/`（或当前激活项目下的 `projects/<id>/workspace/...`）。

其他 CLI：`python cli.py dashboard`、`query-events`、`query-timeline` 等，见 `python cli.py -h`。

## Web 功能概览

- **书库** — 多项目创建、切换、导入
- **工作台** — 开书清单、连写启动、单章运行、长篇指标
- **大纲 / 状态 / 写作台** — 设定、人物伏笔、章节编辑与 AI 改写
- **章节维护** — 待处理章、外审与修稿队列
- **日志中心** — 任务流水、运行日志、费用摘要
- **设置** — 模型路由、Embedding、插件、山山助手

### 多模型路由示例

```yaml
llm:
  default:
    provider: openai
    base_url: https://api.siliconflow.cn/v1
    api_key: sk-xxx
    model: deepseek-ai/DeepSeek-V3
  overrides:
    writer:
      model: Pro/deepseek-ai/DeepSeek-R1
```

## 遗留单文件打包（不推荐）

仅维护兼容时使用：

```powershell
pyinstaller novel_agent.spec --clean --noconfirm
# 输出: dist/NovelAgent.exe — 需自行 `serve --no-browser` 启动 Web
```

**对外分发请用 Electron `栖墨.exe`**，见上文 `electron:pack`。

## 安全与远程部署

默认仅监听 `127.0.0.1`。局域网/服务器部署见 [docs/remote-deployment-security.md](docs/remote-deployment-security.md)。

## 更多文档

- 贡献与发版：[CONTRIBUTING.md](CONTRIBUTING.md)
- 产品介绍：[小说生成Agent项目介绍.md](小说生成Agent项目介绍.md)
- 架构说明：[PROJECT.md](PROJECT.md)
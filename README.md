# 多 Agent 小说生成流水线 MVP

这是第一版本地骨架：先跑通“单章生产流水线”，再接真实模型、数据库和向量检索。

## 当前能力
- Planner 生成章节计划和场景卡。
- Context Builder 生成每个场景的最小上下文包。
- Writer 写单场景。
- Length Fix 根据字数报告分流到 Expander 或 Compressor。
- Stitch Editor 合并并修接缝。
- Style Editor 降低模板感。
- Auditor 输出审校报告和状态更新。
- 自动加载 `prompts/*.md`。
- 审校 JSON 结构校验。
- 敏感词硬匹配扫描。
- `state_update` 自动合并到 `state/*.yaml`。
- 每章生成状态快照。
- 自动生成 HTML 看板。
- 多场景并行生成。
- 自动维护 SQLite 镜像：`data/novel.sqlite`。
- 章节终稿索引入库。
- 事件历史可查询，并会进入后续场景 Context Pack。
- 结构化写作规则：`assets/rules.yaml`。
- 每章自动生成 `chapter_summary.md`，并写入 SQLite。
- 时间线网络：`timeline_nodes`、`timeline_edges`、`foreshadows`、`hooks`。

## 运行测试

```powershell
python -m unittest tests.test_pipeline -v
```

## 干跑一章

当前默认使用 `StaticLLM`，不会调用真实模型，只会生成占位内容。

```powershell
python .\orchestrator.py run-chapter --chapter-id 001 --goal "主角雨夜回到出租屋，并遭遇第一次异常。"
```

输出会落在：

```text
workspace/chapters/chapter_001/
```

旧命令仍兼容：

```powershell
python .\orchestrator.py --chapter-id 001 --goal "主角雨夜回到出租屋，并遭遇第一次异常。"
```

## 重新生成看板

```powershell
python .\orchestrator.py dashboard
```

看板位置：

```text
dashboard/index.html
```

## 查询事件历史

```powershell
python .\orchestrator.py query-events --query "白塔医院"
```

事件来自审校阶段输出的 `state_update.events`。当前干跑模型默认输出空事件；接入真实模型后，只要 Auditor 返回事件，系统会自动写入 `state/events.yaml` 和 `data/novel.sqlite`。

## 查询时间线网络

```powershell
python .\orchestrator.py query-timeline --query "白塔医院"
```

时间线网络来自审校阶段输出的：

```text
state_update.timeline_nodes
state_update.timeline_edges
state_update.foreshadows
state_update.hooks
```

这些内容会同时写入 `state/*.yaml` 和 `data/novel.sqlite`，并自动进入后续场景 Context Pack 的“相关时间线网络”段落。

## Web UI

### 快速启动

**方式一：双击运行**
```
start.bat
```

**方式二：Python 启动**
```powershell
pip install -r requirements.txt
python main.py
```

**方式三：打包好的 exe**
```powershell
dist\NovelAgent.exe
```

启动后自动打开浏览器 http://127.0.0.1:8000

### 功能页面
- **Dashboard** — 总览看板
- **章节管理** — 章节列表、运行新章节、查看详情
- **小说状态** — 人物、伏笔、钩子、道具、事件历史
- **资产编辑** — 编辑人物卡、世界观、文风指南等
- **配置管理** — 查看/编辑 LLM 配置（多模型路由）

### 多模型路由

在 `config/pipeline.yaml` 中配置不同 agent 使用不同模型：

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
    planner:
      model: Pro/deepseek-ai/DeepSeek-R1
```

未配置 override 的 agent 会使用 default 模型。

## 打包 exe

```powershell
pyinstaller novel_agent.spec --clean --noconfirm
```

生成文件：`dist/NovelAgent.exe`（约 33MB）

## 本地验证清单

改代码后请按 [CONTRIBUTING.md](CONTRIBUTING.md) 跑对应检查：

- 前端：`cd web/frontend && npm run build`，再加 `pytest tests/test_workspace_ui_contract.py`
- 后端：`pytest tests/ --ignore=tests/smoke -q`
- 提交前：全量 pytest + smoke 链子集（见 CONTRIBUTING）

首次配置：复制 `config/pipeline.yaml.example` → `config/pipeline.yaml`，填入 API Key。

## 下一步
- 填写 `assets/` 下的人物卡、世界观等资产文件
- 在 `config/pipeline.yaml` 配置真实 LLM API Key
- 增加混合检索和历史上下文召回

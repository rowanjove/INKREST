# 小说生成 Agent 项目文档

> 本文档供 AI 快速理解项目结构、架构和工作流程。  
> **规模（2026-06）**：`novel_agent/` 约 100+ Python 模块 · `web/` 约 25 路由模块 · 前端 `src/` 约 129 个 Vue + 112 个 TS 源文件 · 后端/契约测试 700+ 用例。

## 项目概述

这是一个**多 Agent 协作的小说生成流水线**，通过多个专业化的 AI Agent 协作，自动完成从大纲规划到章节生成的完整流程。产品层提供 **Factory 工厂模式**（5 种运行策略）、书库多项目、Onboarding、Studio 看板与 Electron 桌面壳。

### 核心特性
- 13+ 个专业 Agent 协作生成小说（流水线 phases + checkpoint）
- **Factory 模式**：`project_meta.factory_mode` 经 `runtime_policy` 影响门禁/审校/向量/续跑（见 [FACTORY-MODE-RUNTIME.md](./docs/FACTORY-MODE-RUNTIME.md)）
- 支持多模型路由（不同 Agent 使用不同 LLM）
- SQLite 主状态 + 可关闭的 YAML 镜像（`runtime.yaml_mirror_enabled`）
- 自动审核与重写机制、开书清单 / continue 服务端 readiness
- Vue 3 + FastAPI Web UI，可打包为 Electron 桌面应用

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.8+, FastAPI, uvicorn |
| 前端 | Vue 3, TypeScript, Vite |
| 桌面 | Electron |
| 数据库 | SQLite |
| 向量存储 | numpy (stub 实现) |
| LLM 调用 | httpx, OpenAI 兼容 API |
| 配置 | YAML |

---

## 目录结构

```
小说生成agent/
├── main.py                    # 主入口（serve / run-chapter）
├── orchestrator.py            # CLI 入口（兼容旧命令）
├── requirements.txt           # Python 依赖
├── start.bat                  # Windows 启动脚本
├── generate_presets.py         # 预设生成脚本
│
├── novel_agent/               # 核心代码包
│   ├── __init__.py
│   ├── orchestrator.py        # 流水线编排器（核心）
│   ├── pipeline.py            # 配置管理与 LLM 注册
│   ├── prompts.py             # 提示词加载器
│   ├── rules.py               # 写作规则加载
│   ├── dashboard.py           # 看板生成
│   ├── approval.py            # 审批门控
│   ├── progress.py            # 进度事件发射
│   ├── exceptions.py          # 自定义异常
│   ├── json_utils.py          # JSON 解析工具
│   ├── logging_config.py      # 日志配置
│   ├── migrate.py             # 数据迁移
│   │
│   ├── agents/                # Agent 实现
│   │   ├── base.py            # LLM 客户端基类
│   │   ├── planner.py         # 场景规划
│   │   ├── writer.py          # 场景写作
│   │   ├── length_fix.py      # 字数调整
│   │   ├── stitch_editor.py   # 结构拼接
│   │   ├── style_editor.py    # 文风润色
│   │   ├── auditor.py         # 审核 QA
│   │   ├── chapter_summary.py # 章节总结
│   │   ├── continuity_checker.py # 连续性检查
│   │   ├── context_builder.py # 上下文组装
│   │   └── asset_compressor.py # 素材压缩
│   │
│   ├── state/                 # 状态管理
│   │   ├── manager.py         # 状态管理器
│   │   ├── sqlite_store.py    # SQLite 存储
│   │   └── vector_store.py    # 向量存储
│   │
│   ├── quality/               # 质量检查
│   │   └── audit_schema.py    # 审核报告校验
│   │
│   ├── scripts/               # 工具脚本
│   │   ├── count_chars.py     # 字数统计
│   │   ├── merge_scenes.py    # 场景合并
│   │   └── sensitive_scan.py  # 敏感词扫描
│   │
│   └── exporters/             # 导出器
│       ├── cli.py             # 导出 CLI
│       ├── epub_exporter.py   # EPUB 导出
│       ├── pdf_exporter.py    # PDF 导出
│       └── txt_exporter.py    # TXT 导出
│
├── web/                       # Web 服务
│   ├── server.py              # FastAPI 服务端
│   ├── models.py              # Pydantic 模型
│   ├── tasks.py               # 任务管理
│   └── frontend/              # Vue 前端
│       ├── src/
│       ├── package.json
│       └── vite.config.ts
│
├── prompts/                   # Agent 提示词（Markdown）
│   ├── chief_editor.md        # 总编
│   ├── managing_editor.md     # 主编
│   ├── chapter_planner.md     # 大纲编剧
│   ├── planner.md             # 场景规划
│   ├── writer.md              # 场景写手
│   ├── stitch_editor.md       # 结构拼接
│   ├── style_editor.md        # 文风编辑
│   ├── continuity_checker.md  # 连续性检查
│   ├── auditor.md             # 审核 QA
│   ├── chapter_summary.md     # 章节总结
│   ├── expander.md            # 扩写
│   ├── compressor.md          # 压缩
│   └── asset_compressor.md    # 素材压缩
│
├── assets/                    # 资产文件
│   ├── character_cards.yaml   # 人物卡
│   ├── world_bible.md         # 世界观
│   ├── style_guide.md         # 文风指南
│   ├── rules.yaml             # 写作规则
│   └── sensitive_words.txt    # 敏感词表
│
├── config/                    # 配置
│   └── pipeline.yaml          # 流水线配置
│
├── state/                     # 运行时状态
│   ├── events.yaml            # 事件库
│   ├── foreshadows.yaml       # 伏笔库
│   ├── hooks.yaml             # 钩子库
│   ├── objects.yaml           # 道具库
│   ├── threads.yaml           # 故事线
│   ├── timeline_nodes.yaml    # 时间线节点
│   ├── timeline_edges.yaml    # 时间线边
│   ├── continuity_state.yaml  # 连续性状态
│   ├── snapshots/             # 章节快照
│   └── archive/               # 归档
│
├── data/                      # 数据
│   └── novel.sqlite           # SQLite 数据库
│
├── workspace/                 # 工作区
│   └── chapters/              # 章节输出
│       └── chapter_XXX/       # 单章目录
│           ├── plan.json      # 章节计划
│           ├── scene_XXX_context.md  # 场景上下文
│           ├── scenes/        # 场景正文
│           ├── chapter_raw.txt    # 合并后初稿
│           ├── chapter_merged.txt # 拼接后稿件
│           ├── chapter_final.txt  # 终稿
│           ├── chapter_summary.md # 章节总结
│           ├── state_update.json  # 状态更新
│           ├── checkpoint.json    # 检查点
│           └── reports/       # 审核报告
│               ├── audit.json
│               ├── continuity.json
│               ├── wordcount.json
│               └── sensitive_scan.json
│
├── dashboard/                 # 看板
│   └── index.html
│
├── presets/                   # 预设模板
│   ├── male_xuanhuan_*/       # 男频玄幻
│   ├── female_xiandai_*/      # 女频现代
│   └── ...                    # 更多类型
│
├── tests/                     # 测试
│   └── test_pipeline.py
│
├── docs/                      # 文档
│   └── superpowers/
│
└── 参考/                      # 参考资料
    ├── 多Agent小说生成方案.md
    ├── 内置提示词原文.md
    └── ...
```

---

## Agent 流水线架构

### 流水线步骤

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           章节生成流水线                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Step 1: Planner (场景规划)                                                  │
│     ↓ 输入: chapter_goal                                                    │
│     ↓ 输出: plan.json (场景卡列表)                                           │
│                                                                             │
│  Step 2: Writer x N (并行场景写作)                                           │
│     ↓ 输入: 场景卡 + Context Pack                                           │
│     ↓ 输出: scenes/scene_XXX.txt                                            │
│                                                                             │
│  Step 3: Merge (场景合并)                                                    │
│     ↓ 输入: scenes/*.txt                                                    │
│     ↓ 输出: chapter_raw.txt                                                 │
│                                                                             │
│  Step 4: Stitch Editor (结构拼接)                                            │
│     ↓ 输入: chapter_raw.txt                                                 │
│     ↓ 输出: chapter_merged.txt                                              │
│                                                                             │
│  Step 5: Style Editor (文风润色)                                             │
│     ↓ 输入: chapter_merged.txt                                              │
│     ↓ 输出: chapter_final.txt                                               │
│                                                                             │
│  Step 6: Continuity Checker (连续性检查)                                     │
│     ↓ 输入: chapter_final.txt + 状态库                                      │
│     ↓ 输出: reports/continuity.json                                         │
│                                                                             │
│  Step 7: Chapter Summary (章节总结)                                          │
│     ↓ 输入: chapter_final.txt                                               │
│     ↓ 输出: chapter_summary.md                                              │
│                                                                             │
│  Step 8: Word Count (字数统计)                                               │
│     ↓ 输出: reports/wordcount.json                                          │
│                                                                             │
│  Step 9: Auditor (审核 QA)                                                   │
│     ↓ 输入: chapter_final.txt                                               │
│     ↓ 输出: reports/audit.json + state_update.json                          │
│                                                                             │
│  Step 10: Auto-Rewrite (自动重写，如果 risk_level=高)                         │
│     ↓ 策略: plan 级问题 → 重新规划; text 级问题 → 局部润色                    │
│                                                                             │
│  Step 11: Sensitive Scan (敏感词扫描)                                        │
│     ↓ 输出: reports/sensitive_scan.json                                     │
│                                                                             │
│  Step 12: Approval Gate (审批门控)                                           │
│     ↓ 交互模式下需要人工确认                                                  │
│                                                                             │
│  Step 13: State Update (状态持久化)                                          │
│     ↓ 写入: SQLite + YAML 状态文件                                           │
│                                                                             │
│  Step 14: Vector Index (向量索引)                                            │
│     ↓ 索引章节到向量存储                                                     │
│                                                                             │
│  Step 15: Dashboard (看板更新)                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 检查点机制

支持断点续传，分三个检查点：
1. **generation** — 场景生成 + 合并 + 拼接 + 润色
2. **audit** — 连续性检查 + 总结 + 字数 + 审核 + 重写
3. **state_update** — 敏感词扫描 + 审批 + 状态持久化

---

## Agent 职责一览

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **Chief Editor** | 生成宏观大纲 | 主题、类型 | 总纲 JSON |
| **Managing Editor** | 拆分阶段剧情 | 总纲 | 章节队列 JSON |
| **Chapter Planner** | 扩展章节梗概 | 章节目标 | 梗概 JSON |
| **Planner** | 拆分场景卡 | 章节梗概 | 场景卡 JSON |
| **Writer** | 写单场景正文 | 场景卡 + 上下文 | 小说正文 |
| **Stitch Editor** | 合并场景 | 多场景正文 | 连贯初稿 |
| **Style Editor** | 文风润色 | 初稿 | 润色后正文 |
| **Continuity Checker** | 连续性检查 | 正文 + 状态库 | 问题报告 JSON |
| **Auditor** | 审核 QA | 正文 | 审核报告 + 状态更新 |
| **Chapter Summary** | 章节总结 | 终稿 | Markdown 摘要 |
| **Expander** | 扩写 | 正文 + 目标字数 | 扩写后正文 |
| **Compressor** | 压缩 | 正文 + 目标字数 | 压缩后正文 |
| **Asset Compressor** | 素材压缩 | 状态库 | 压缩建议 JSON |
| **Context Builder** | 组装上下文 | 场景卡 + 状态 | 上下文 Markdown |

---

## LLM 配置

### 配置文件位置
`config/pipeline.yaml`

### 配置格式

```yaml
llm:
  default:
    provider: openai          # 或 "static" 用于测试
    base_url: https://api.siliconflow.cn/v1
    api_key: ${SILICONFLOW_API_KEY}  # 支持环境变量替换
    model: deepseek-ai/DeepSeek-V3
    max_tokens: 4096
    temperature: 0.7
  overrides:
    writer:
      model: Pro/deepseek-ai/DeepSeek-R1  # 写手用更强模型
    planner:
      model: Pro/deepseek-ai/DeepSeek-R1
    auditor:
      model: deepseek-ai/DeepSeek-V3

runtime:
  max_workers: 4              # 并行场景数
  retry_attempts: 1
  max_rewrites: 2             # 最大重写次数
  interactive: false          # 是否启用审批门控

chapter:
  default_target_chars: [1200, 2200]
  default_scene_target_chars: [400, 800]

embedding:
  provider: stub              # 或 "openai"
```

### 模型库（可选）
`config/models.json`

```json
{
  "models": {
    "deepseek-v3": {
      "provider": "openai",
      "base_url": "https://api.siliconflow.cn/v1",
      "model": "deepseek-ai/DeepSeek-V3"
    },
    "deepseek-r1": {
      "provider": "openai",
      "base_url": "https://api.siliconflow.cn/v1",
      "model": "Pro/deepseek-ai/DeepSeek-R1"
    }
  }
}
```

---

## 启动方式

### 方式一：Web UI（推荐）

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
# 或
python main.py serve --host 127.0.0.1 --port 8000

# 浏览器自动打开 http://127.0.0.1:8000
```

### 方式二：CLI 生成章节

```bash
# 干跑模式（使用 StaticLLM，不调用真实模型）
python main.py run-chapter --chapter-id 001 --goal "主角雨夜回到出租屋" --dry-run

# 真实模式
python main.py run-chapter --chapter-id 001 --goal "主角雨夜回到出租屋"

# JSON 输出（供 Electron IPC 使用）
python main.py run-chapter --chapter-id 001 --goal "..." --json-output
```

### 方式三：桌面端 Electron（推荐分发）

```powershell
cd web/frontend
npm run electron:pack
# 输出: dist-desktop/win-unpacked/栖墨.exe
```

### 方式三（遗留）：PyInstaller 单文件

```bash
pyinstaller novel_agent.spec --clean --noconfirm
# 输出: dist/NovelAgent.exe — 需 main.py serve 启动 Web
```

### 方式四：Windows 双击启动

```
start.bat
```

---

## Web API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects` | 项目列表 |
| POST | `/api/projects` | 创建项目 |
| GET | `/api/chapters` | 章节列表 |
| POST | `/api/chapters/run` | 运行章节生成 |
| GET | `/api/chapters/{id}` | 章节详情 |
| GET | `/api/state` | 小说状态 |
| GET | `/api/timeline` | 时间线 |
| GET | `/api/config` | 配置 |
| PUT | `/api/config` | 更新配置 |
| GET | `/api/assets` | 资产列表 |
| PUT | `/api/assets/{type}` | 更新资产 |
| GET | `/api/dashboard` | 看板 HTML |
| WS | `/ws/progress` | WebSocket 进度推送 |

---

## 状态管理

### 双写机制
- **SQLite** (`data/novel.sqlite`) — 主存储，支持查询和索引
- **YAML** (`state/*.yaml`) — 兼容旧工具，便于人工查看

### 状态类型
| 文件 | 内容 |
|------|------|
| events.yaml | 事件库 |
| characters (SQLite) | 角色状态 |
| objects.yaml | 道具库 |
| foreshadows.yaml | 伏笔库 |
| hooks.yaml | 钩子库 |
| threads.yaml | 故事线 |
| timeline_nodes.yaml | 时间线节点 |
| timeline_edges.yaml | 时间线边 |

### 快照机制
每次状态更新前自动创建快照，存储在 `state/snapshots/chapter_XXX/`。

---

## 提示词系统

### 加载机制
- `novel_agent/prompts.py` 中的 `PromptRepository` 类负责加载
- 自动扫描 `prompts/*.md` 文件
- 按文件名映射到 Agent role

### 提示词结构（统一格式）
每个提示词文件包含：
1. **角色定义** — Agent 身份
2. **职责边界** — 只做/不做
3. **输入要求** — 期望接收什么
4. **操作原则** — 具体指导
5. **输出格式** — JSON/Markdown 格式
6. **字段说明** — 类型、必填、枚举值
7. **质量检查清单** — 输出前自查

---

## 关键设计决策

### 1. 并行场景生成
- 使用 `ThreadPoolExecutor` 并行生成多个场景
- `max_workers` 控制并发数
- 单个场景失败不阻塞其他场景

### 2. 分层重写策略
当审核发现高风险问题时：
- **plan 级问题** → 重新规划场景，重新生成
- **text 级问题** → 局部润色

### 3. 上下文组装
`ContextBuilderAgent` 为每个场景组装最小上下文包：
- 本章目标
- 当前场景卡
- 人物资产
- 当前状态
- 相关历史事件
- 相关时间线网络
- 语义相关片段（向量召回）
- 世界观
- 文风规范
- 写作规则

### 4. 多模型路由
不同 Agent 可以使用不同模型：
- Writer、Planner → 强模型（如 DeepSeek-R1）
- Auditor、Style Editor → 标准模型（如 DeepSeek-V3）
- 未配置 override 的 agent 使用 default 模型

---

## 开发指南

### 运行测试
```bash
python -m pytest tests/ --ignore=tests/smoke -q
cd web/frontend && npm run test:unit && npm run build
```

### 添加新 Agent
1. 在 `novel_agent/agents/` 创建新文件
2. 继承 `PromptAgent` 或 `base.py` 中的基类
3. 在 `prompts/` 添加对应提示词
4. 在 `orchestrator.py` 中集成

### 添加新导出格式
1. 在 `novel_agent/exporters/` 创建新文件
2. 实现导出逻辑
3. 在 `cli.py` 中注册

---

## 常见问题

### Q: 如何接入真实模型？
修改 `config/pipeline.yaml`，将 `provider` 从 `static` 改为 `openai`，并配置 `base_url` 和 `api_key`。

### Q: 如何查看生成过程？
- Web UI 的章节详情页
- `logs/novel_agent.log`
- WebSocket `/ws/progress` 实时推送

### Q: 如何自定义写作类型？
1. 编辑 `assets/world_bible.md` 定义世界观
2. 编辑 `assets/character_cards.yaml` 定义人物
3. 编辑 `assets/style_guide.md` 定义文风
4. 或使用 `presets/` 中的预设模板

### Q: 状态文件损坏怎么办？
- SQLite 有快照机制，可从 `state/snapshots/` 恢复
- 运行 `python -m novel_agent.migrate` 进行数据迁移

---

## 项目规模

| 指标 | 数值 |
|------|------|
| Python 文件 | ~30 个 |
| 提示词文件 | 13 个 |
| Agent 数量 | 13 个 |
| 流水线步骤 | 15 步 |
| 代码行数 | ~5000 行 |

---

## 更新日志

- **2026-05-23** — 优化所有 Agent 提示词，统一格式，增加字段说明和质量检查清单
- **2026-05-22** — 项目初始开发，完成 MVP 流水线

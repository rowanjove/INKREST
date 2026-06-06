# 小说生成 Agent — 项目详细介绍

## 一、项目概述

小说生成 Agent 是一套**多 Agent 协同的中文网文自动创作系统**。它将长篇小说的章节生成拆解为 10 个专职 AI Agent 角色（规划师、写手、编辑、审计等），按 15 步流水线依次执行，并提供完整的 Web 管理界面和 Electron 桌面应用。

**核心理念：** 每一章的生成不只是"写一段文字"，而是经过规划、创作、缝合、润色、连贯性检查、审计、敏感词扫描、状态更新、向量索引等完整流程，确保长篇连载中的逻辑一致性和质量可控性。

**技术栈：**
- 后端：Python + FastAPI + SQLite + httpx
- 前端：Vue 3 + TypeScript + Vite + Pinia + Element Plus + Vue Router
- 桌面端：Electron（已预构建发行版）
- 向量检索：numpy 余弦相似度（轻量本地方案）

---

## 二、目录结构

```
小说生成agent/
├── main.py                    # 入口：启动 Web 服务或 CLI 运行章节
├── orchestrator.py            # CLI 版编排器（旧版）
├── generate_presets.py        # 生成 28 个内置类型预设的脚本
├── requirements.txt           # Python 依赖
├── start.bat                  # Windows 一键启动脚本
├── README.md                  # 项目 README
│
├── config/                    # 项目级配置
│   └── pipeline.yaml          #   流水线设置（LLM、runtime、章节参数）
│
├── novel_agent/               # 核心 Python 包
│   ├── orchestrator.py        #   15 步章节流水线编排器
│   ├── pipeline.py            #   PipelineConfig：加载配置、创建 LLM 客户端
│   ├── prompts.py             #   提示词仓库（读取 prompts/*.md）
│   ├── rules.py               #   写作规则书（加载 rules.yaml）
│   ├── approval.py            #   人工审批门
│   ├── dashboard.py           #   HTML 仪表盘生成
│   ├── progress.py            #   JSON 进度事件发射（Electron IPC）
│   ├── json_utils.py          #   健壮的 JSON 解析器
│   ├── exceptions.py          #   自定义异常
│   ├── logging_config.py      #   日志配置
│   │
│   ├── agents/                #   10 个专职 Agent
│   │   ├── base.py            #     基类：PromptAgent / OpenAILLM / FallbackLLM
│   │   ├── planner.py         #     规划师：章节目标 → 场景卡
│   │   ├── writer.py          #     写手：场景卡 → 散文
│   │   ├── context_builder.py #     上下文组装器
│   │   ├── length_fix.py      #     字数修正（扩写/压缩）
│   │   ├── stitch_editor.py   #     缝合编辑
│   │   ├── style_editor.py    #     风格编辑
│   │   ├── continuity_checker.py #  连贯性检查
│   │   ├── chapter_summary.py #     章节总结
│   │   ├── auditor.py         #     审计员
│   │   └── asset_compressor.py#     状态压缩器
│   │
│   ├── state/                 #   状态管理
│   │   ├── manager.py         #     StateManager：应用状态更新
│   │   ├── sqlite_store.py    #     SQLite 后端（10 张表）
│   │   └── vector_store.py    #     向量存储（numpy + 余弦相似度）
│   │
│   ├── scripts/               #   工具脚本
│   │   ├── count_chars.py     #     中文字符计数
│   │   ├── merge_scenes.py    #     场景合并
│   │   └── sensitive_scan.py  #     敏感词扫描
│   │
│   └── exporters/             #   导出模块
│       ├── txt_exporter.py    #     纯文本导出
│       ├── epub_exporter.py   #     EPUB 导出
│       └── pdf_exporter.py    #     PDF 导出
│
├── web/                       # Web 应用
│   ├── server.py              #   FastAPI 后端（~40 个 API 端点）
│   ├── models.py              #   Pydantic 请求/响应模型
│   ├── tasks.py               #   TaskManager：后台任务执行
│   └── frontend/              #   Vue 3 前端 SPA
│       └── src/
│           ├── api.ts         #     Axios API 客户端
│           ├── router.ts      #     Vue Router（9 个路由）
│           ├── views/         #     7 个页面视图
│           ├── components/    #     19 个 UI 组件
│           └── stores/        #     Pinia 状态管理
│
├── prompts/                   # 提示词模板（10 个角色）
├── presets/                   # 28 个内置类型预设
├── assets/                    # 小说素材文件
├── state/                     # 持久化状态（YAML + 快照）
├── workspace/                 # 生成的章节输出
├── data/                      # SQLite 数据库
└── dashboard/                 # 生成的 HTML 仪表盘
```

---

## 三、核心流水线：15 步章节生成

每一章的生成经过以下 15 个步骤，由 `NovelOrchestrator` 编排：

```
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1: 规划 (Planner)                                             │
│  章节目标 → JSON 计划（章节标题、目标字数、场景卡列表）               │
├─────────────────────────────────────────────────────────────────────┤
│  Step 2: 并行场景生成 (Writer × N)                                   │
│  每个场景：组装上下文 → 写手生成散文 → 字数修正                       │
│  场景间通过 ThreadPoolExecutor 并行执行                               │
├─────────────────────────────────────────────────────────────────────┤
│  Step 3: 场景合并                                                    │
│  按场景顺序拼接为章节原始文本                                         │
├─────────────────────────────────────────────────────────────────────┤
│  Step 4: 缝合编辑 (Stitch Editor)                                    │
│  修复场景间的衔接裂缝，不改变情节                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Step 5: 风格编辑 (Style Editor)                                     │
│  消除模板感、模糊用语和"AI 味"                                       │
├─────────────────────────────────────────────────────────────────────┤
│  Step 6: 连贯性检查 (Continuity Checker)                             │
│  对照当前状态检查角色矛盾、物品冲突等                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Step 7: 写入最终文本                                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Step 8: 章节总结 (Chapter Summary)                                  │
│  生成结构化 Markdown 总结（概述、角色发展、看点、伏笔、张力心电图）    │
├─────────────────────────────────────────────────────────────────────┤
│  Step 9: 字数统计                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Step 10: 审计 (Auditor)                                             │
│  全面审计：设定冲突、角色状态冲突、物品归属冲突                       │
│  输出：risk_level（低/中/高）、issues、state_update                   │
│  ── 若 risk_level == "高"，自动触发重写循环（最多 N 次）──           │
│  重写流程：审计问题注入 → 风格编辑 → 连贯性检查 → 重新审计           │
├─────────────────────────────────────────────────────────────────────┤
│  Step 11: 敏感词扫描                                                 │
│  硬匹配 assets/sensitive_words.txt                                   │
├─────────────────────────────────────────────────────────────────────┤
│  Step 12: 审批门 (Approval Gate)                                     │
│  交互模式：人工确认；非交互模式：自动通过                             │
├─────────────────────────────────────────────────────────────────────┤
│  Step 13: 状态更新                                                   │
│  将审计的 state_update 写入 SQLite + YAML 快照                       │
├─────────────────────────────────────────────────────────────────────┤
│  Step 14: 向量索引                                                   │
│  章节文本分块 → Embedding → 存入向量库（用于后续语义检索）            │
├─────────────────────────────────────────────────────────────────────┤
│  Step 15: 更新仪表盘                                                 │
│  重新生成 HTML 仪表盘                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 四、Agent 角色详解

### 4.1 基础架构 (`agents/base.py`)

| 类 | 用途 |
|---|---|
| `LLMClient` (Protocol) | 统一接口：`generate(role, prompt) → str` |
| `StaticLLM` | 确定性占位实现，用于测试和干跑 |
| `OpenAILLM` | OpenAI 兼容 HTTP 客户端，支持重试、代理、调用日志（token/延迟） |
| `FallbackLLM` | 主模型 + 备选链，逐个尝试直到成功 |
| `PromptAgent` | 所有 Agent 的基类，绑定角色和 LLM |

**LLM 配置支持：**
- 扁平格式：所有 Agent 共用一个模型
- 嵌套格式：`default` + `overrides`，可为不同 Agent 指定不同模型
- `model_ref`：引用 `config/models.json` 中的模型库条目，避免重复配置
- `fallback_models`：指定备选模型链

### 4.2 十大 Agent 角色

| 角色 | 类 | 输入 | 输出 | 说明 |
|------|---|------|------|------|
| **规划师** | `PlannerAgent` | 章节目标 | JSON 计划 | 分解为场景卡，每卡含目的、入口、出口、必含/禁含要素 |
| **写手** | `WriterAgent` | 上下文包 | 场景散文 | 接收世界设定、角色卡、历史、风格指南等完整上下文 |
| **上下文组装器** | `ContextBuilderAgent` | 目标+场景 | 上下文文本 | 从 SQLite 检索相关事件、从向量库召回历史片段 |
| **字数修正** | `LengthFixAgent` | 散文+目标范围 | 修正后散文 | 超出→压缩，不足→扩写 |
| **缝合编辑** | `StitchEditorAgent` | 合并文本 | 修正文本 | 修复场景衔接，不改情节 |
| **风格编辑** | `StyleEditorAgent` | 文本 | 润色文本 | 去模板感、去 AI 味 |
| **连贯性检查** | `ContinuityCheckerAgent` | 文本+状态 | JSON 报告 | 检查角色/物品/设定矛盾 |
| **章节总结** | `ChapterSummaryAgent` | 最终文本 | Markdown 总结 | 结构化：概述、角色发展、看点、伏笔、张力曲线 |
| **审计员** | `AuditorAgent` | 最终文本 | JSON 审计报告 | 风险等级（低/中/高）+ 问题列表 + 状态更新 |
| **状态压缩器** | `AssetCompressorAgent` | 当前状态 | 压缩状态 | 归档已关闭线程、清除过期事件 |

---

## 五、状态管理系统

### 5.1 SQLite 后端 (`state/sqlite_store.py`)

10 张数据表，覆盖小说创作的全部状态维度：

| 表名 | 存储内容 |
|------|---------|
| `events` | 事件流（时间戳、章节、描述） |
| `objects` | 物品清单（名称、持有者、状态） |
| `threads` | 故事线程（开启/关闭状态） |
| `character_state` | 角色状态快照 |
| `chapters` | 章节元数据 |
| `chapter_summaries` | 章节总结 |
| `timeline_nodes` | 时间线实体节点 |
| `timeline_edges` | 时间线关联边 |
| `foreshadows` | 伏笔（埋设/揭示/遗忘） |
| `hooks` | 钩子（读者吸引力点） |

### 5.2 向量存储 (`state/vector_store.py`)

- 基于 numpy 的轻量本地方案
- 每次章节完成后，将章节总结 + 正文分块存入向量库
- 支持余弦相似度检索 + 元数据过滤
- 配置为 `stub` 时跳过向量索引

### 5.3 状态更新流程

```
审计报告 (state_update)
    ↓
StateManager.apply_update()
    ↓
SQLite 写入（events/objects/threads/characters/timeline）
    ↓
YAML 快照存档（state/snapshots/chapter_XXX/）
```

---

## 六、Web 应用

### 6.1 后端 API（FastAPI，约 40 个端点）

| 模块 | 端点 | 功能 |
|------|------|------|
| **项目** | `GET/POST/DELETE /api/projects` | 多项目管理，支持切换和旧版迁移 |
| **预设** | `GET/POST/DELETE /api/presets` | 28 个类型预设的 CRUD 和应用 |
| **模型库** | `GET/POST/DELETE /api/models` | LLM 模型配置管理，支持连通性测试 |
| **章节** | `POST /api/chapters/run` | 单章生成 |
| | `POST /api/chapters/run-batch` | 批量章节生成（串行，状态依赖） |
| | `GET /api/chapters` | 章节列表 |
| | `GET /api/chapters/{id}` | 章节详情（计划/正文/审计/字数/连贯性/总结） |
| **状态** | `GET /api/state` | 角色/伏笔/钩子/物品/事件/线程 |
| | `GET /api/state/timeline` | 时间线网络 |
| | `GET /api/events` | 事件搜索 |
| **素材** | `GET/PUT /api/assets/{name}` | 角色卡/世界设定/风格指南/规则/敏感词 |
| **配置** | `GET/PUT /api/config` | 流水线配置（含密钥遮罩） |
| **提示词** | `GET/PUT/POST /api/prompts/{role}` | 提示词编辑和重置 |
| **LLM 日志** | `GET /api/llm-logs` | 调用日志聚合（Token/延迟/模型） |
| **导出** | `POST /api/export` | TXT/EPUB/PDF 导出 |
| **数据库** | `POST /api/database/clear` | 清空数据库 |
| **WebSocket** | `/ws/tasks` | 实时任务进度推送 |

### 6.2 前端页面（Vue 3 SPA，9 个路由）

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | 项目库 | 创建/切换/删除项目，选择类型预设 |
| `/workspace` | 工作台 | 仪表盘统计、最近章节、任务日志、快速启动章节 |
| `/chapters` | 章节列表 | 已生成章节一览、批量生成对话框 |
| `/chapters/:id` | 章节详情 | 计划/正文/审计/字数/连贯性/状态更新/总结 |
| `/state` | 小说状态 | 角色/伏笔/钩子/物品/线程/事件浏览 |
| `/timeline` | 时间线 | 节点-边网络、伏笔/钩子时间轴 |
| `/assets` | 素材编辑 | 角色卡/世界设定/风格指南/规则/敏感词编辑 |
| `/config` | 设置 | 模型库管理、Embedding 配置、LLM 配置（多模型路由+fallback）、调用日志、提示词编辑、数据管理 |
| `/tasks` | 任务监控 | 实时任务进度、日志流 |

### 6.3 关键前端组件

| 组件 | 功能 |
|------|------|
| `PresetSelector` | 类型预设选择器（男频/女频双通道） |
| `ModelLibrary` | 模型库 CRUD + 连通性测试 |
| `LLMConfig` | LLM 配置（默认模型/Agent 路由/Fallback 链） |
| `EmbeddingConfig` | 向量检索配置（stub/openai） |
| `LLMLogViewer` | 调用日志面板（Token 汇总/角色分组/详细记录） |
| `PromptManager` | 提示词模板编辑器（支持重置为默认） |
| `DataManager` | 数据库管理（清空操作） |

---

## 七、类型预设系统

### 7.1 预设结构

每个预设是一个目录，包含：
- `meta.json`：元数据（id、名称、频道、分类、标签、描述）
- `guide.md`：类型写作指南（风格特征、结构规范、节奏模式、禁忌、对话风格）
- `prompt_overrides/`（可选）：覆盖默认提示词的角色专用提示词

### 7.2 内置预设（28 个）

**男频（16 个）：**

| ID | 名称 | 分类 |
|----|------|------|
| xuanhuan_dongfang | 东方玄幻 | 玄幻 |
| xuanhuan_fanpai | 反派玄幻 | 玄幻 |
| xuanhuan_jiazu | 家族玄幻 | 玄幻 |
| xianxia_fanliu | 凡人流仙侠 | 仙侠 |
| wuxia_chuantong | 传统武侠 | 武侠 |
| kehuan_xingji | 星际科幻 | 科幻 |
| kehuan_moshi | 末世科幻 | 科幻 |
| dushi_shenhao | 都市神豪 | 都市 |
| dushi_yineng | 都市异能 | 都市 |
| lishi_jiak | 架空历史 | 历史 |
| qihuan_xihuan | 西方奇幻 | 奇幻 |
| xuanyi_guize | 规则悬疑 | 悬疑 |
| youxi_xunini | 游戏虚拟 | 游戏 |
| zhutian_wuxian | 诸天无限 | 诸天 |

**女频（12 个）：**

| ID | 名称 | 分类 |
|----|------|------|
| xiandai_zongcai | 现代总裁 | 现代言情 |
| xiandai_anlian | 暗恋爱恋 | 现代言情 |
| xiandai_majia | 马甲文 | 现代言情 |
| xiandai_tianchong | 甜宠文 | 现代言情 |
| gongdou_hougong | 宫斗后宫 | 古代言情 |
| gudai_zhaidou | 宅斗文 | 古代言情 |
| xianxia_shitu | 仙侠师徒 | 仙侠言情 |
| chuangyue_gudai | 穿越古代 | 穿越 |
| chungai_ashuang | 纯爱暗爽 | 纯爱 |
| kuaichuan_gonglue | 快穿攻略 | 快穿 |
| niandai_qishi | 年代骑士 | 年代文 |
| wuxp_denvzhu | 无 CP 大女主 | 大女主 |

---

## 八、素材文件

| 文件 | 用途 | 说明 |
|------|------|------|
| `character_cards.yaml` | 角色设定库 | 每个角色的姓名、性格、能力、关系、当前状态 |
| `world_buide.md` | 世界设定 | 地理、势力、魔法体系、科技水平等 |
| `style_guide.md` | 风格指南 | 叙述视角、文风偏好、节奏要求 |
| `rules.yaml` | 写作规则书 | 常用词/禁用词、常用句式/禁用句式、写作技法 |
| `sensitive_words.txt` | 敏感词表 | 硬匹配扫描，逐行列出 |

---

## 九、配置系统

### 9.1 流水线配置 (`config/pipeline.yaml`)

```yaml
chapter:
  default_target_chars: [1200, 2200]       # 章节目标字数范围
  default_scene_target_chars: [400, 800]   # 场景目标字数范围
runtime:
  max_workers: 4          # 并行场景生成的最大线程数
  retry_attempts: 1       # 重试次数
  max_rewrites: 2         # 审计高风险时的最大自动重写次数
llm:
  provider: openai        # LLM 提供商（static/openai）
  base_url: https://api.openai.com/v1
  api_key: sk-xxx
  model: gpt-4o-mini
  # 或嵌套格式：
  # default: { provider: openai, model: gpt-4o-mini }
  # overrides:
  #   writer: { model: gpt-4o }
  #   auditor: { model: gpt-4o }
embedding:
  provider: openai        # Embedding 提供商（stub/openai）
  base_url: https://api.openai.com/v1
  api_key: sk-xxx
  model: text-embedding-3-small
```

### 9.2 模型库 (`config/models.json`)

集中管理多个 LLM 模型配置，供流水线通过 `model_ref` 引用：

```json
{
  "models": {
    "gpt4o": {
      "provider": "openai",
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-xxx",
      "model": "gpt-4o",
      "timeout": 120
    },
    "deepseek": {
      "provider": "openai",
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "sk-xxx",
      "model": "deepseek-chat"
    }
  }
}
```

---

## 十、高级特性

### 10.1 审计自动重写

当审计员判定 `risk_level == "高"` 时，自动进入重写循环：

1. 将审计发现的问题作为反馈注入风格编辑器
2. 重新执行风格编辑 → 连贯性检查 → 审计
3. 若风险仍为"高"，重复上述流程（最多 `max_rewrites` 次）
4. 循环结束后继续后续步骤

### 10.2 Token/耗时追踪

- 每次 LLM 调用记录：`role`、`model`、`prompt_tokens`、`completion_tokens`、`total_tokens`、`latency_ms`、`timestamp`
- `FallbackLLM` 聚合所有 client 的调用日志
- 任务完成后日志存入 TaskManager
- 前端 LLM 日志面板展示：汇总统计、按角色分组、详细调用记录

### 10.3 模型 Fallback 机制

```yaml
llm:
  default:
    provider: openai
    model: gpt-4o-mini
  overrides:
    writer:
      model_ref: gpt4o          # 从模型库引用
      fallback_models:           # 备选模型链
        - deepseek
        - qwen
```

当主模型调用失败时，自动依次尝试备选模型。

### 10.4 批量章节生成

- 一次提交多个章节，按顺序自动执行
- 后续章节使用前面章节的状态更新（状态依赖）
- 每章独立任务 ID，可在任务监控中查看各自进度

### 10.5 多项目管理

- 每个项目独立目录（`projects/{id}/`）
- 独立的配置、素材、状态、提示词
- 支持从旧版平目录结构自动迁移
- 项目间可切换，支持应用类型预设

### 10.6 导出功能

支持三种格式的全书/选章导出：
- **TXT**：纯文本
- **EPUB**：电子书格式
- **PDF**：文档格式

---

## 十一、启动方式

### 命令行启动

```bash
pip install -r requirements.txt
python main.py
```

### Windows 一键启动

双击 `start.bat`，自动安装依赖并启动。

### 桌面应用

`dist-desktop/` 目录包含预构建的 Electron 桌面应用，双击即可运行。

启动后访问 `http://localhost:8000` 进入 Web 界面。

---

## 十二、技术架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Electron 桌面壳（可选）                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Vue 3 SPA 前端 (Vite + Pinia + Element Plus) │  │
│  │  ┌──────┐ ┌────────┐ ┌────────┐ ┌──────┐ ┌───────────┐  │  │
│  │  │项目库│ │工作台  │ │章节列表│ │ 状态 │ │ 设置      │  │  │
│  │  └──────┘ └────────┘ └────────┘ └──────┘ └───────────┘  │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │ HTTP / WebSocket                  │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │              FastAPI 后端 (server.py)                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐  │  │
│  │  │ProjectMgr│ │PresetMgr│ │ModelLib  │ │ TaskManager │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────────┘  │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │         NovelOrchestrator (15 步流水线)                    │  │
│  │                                                           │  │
│  │  ┌────────┐ ┌──────┐ ┌──────────┐ ┌──────────┐          │  │
│  │  │Planner │→│Writer│→│StitchEdit│→│StyleEdit │          │  │
│  │  └────────┘ └──────┘ └──────────┘ └──────────┘          │  │
│  │       ↓         ↓          ↓            ↓                │  │
│  │  ┌────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐        │  │
│  │  │ContChk │→│Summarizer│→│Auditor │→│Sensitive │        │  │
│  │  └────────┘ └──────────┘ └────────┘ └──────────┘        │  │
│  │                              ↓                            │  │
│  │                    ┌──────────────────┐                   │  │
│  │                    │  Auto-Rewrite    │                   │  │
│  │                    │  Loop (if 高风险)│                   │  │
│  │                    └──────────────────┘                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │  持久化层                                                  │  │
│  │  ┌──────────┐ ┌──────────────┐ ┌──────────────────────┐  │  │
│  │  │ SQLite   │ │ YAML 快照    │ │ numpy 向量库         │  │  │
│  │  │ (10 表)  │ │ (state/)     │ │ (vector_store/)     │  │  │
│  │  └──────────┘ └──────────────┘ └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 十三、已生成内容

目前已成功生成 11 章（chapter_001 ~ chapter_011），每章包含完整的中间产物和最终文本，可供查看和导出。

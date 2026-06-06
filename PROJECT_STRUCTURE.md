# 小说生成 Agent — 项目结构文档

> 自动生成于 2026-05-26

---

## 一、技术栈

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 主语言 |
| FastAPI | 0.104+ | Web 框架 |
| uvicorn | 0.24+ | ASGI 服务器 |
| httpx | - | LLM API 调用 |
| Pydantic v2 | - | 数据校验 |
| PyYAML | 6+ | 配置解析 |
| SQLite | 内置 (WAL模式) | 主数据库 |
| NumPy | 1.24+ | 向量相似度计算 |
| websockets | - | 实时推送 |

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.5+ | SPA 框架 |
| TypeScript | ~6.0 | 类型安全 |
| Vite | 8+ | 构建工具 |
| Element Plus | 2.14+ | UI 组件库 |
| Pinia | 3+ | 状态管理 |
| vue-router | 4.6+ | 路由 |
| axios | - | HTTP 客户端 |
| Electron | 42+ | 桌面打包 |

---

## 二、目录结构

```
小说生成agent/
├── main.py                    # 入口：双模式（Web服务 / CLI章节生成）
├── orchestrator.py            # 旧版 CLI 编排器（向后兼容）
├── requirements.txt           # Python 依赖
├── start.bat                  # Windows 启动脚本
├── projects.json              # 多项目注册表
├── generate_presets.py        # 预设生成脚本
├── .env.example               # API Key 模板
├── novel_agent.spec           # PyInstaller 打包配置（完整应用）
├── novel-agent-backend.spec   # PyInstaller 打包配置（仅后端）
│
├── novel_agent/               # 核心 Python 包
│   ├── agents/                # 13 个专职 AI Agent
│   ├── control/               # 叙事控制（校准、尺度、体裁基因、叙事债务）
│   ├── exporters/             # 小说导出（TXT / EPUB / PDF）
│   ├── phases/                # 流水线阶段（生成 / 审计 / 后审计）
│   ├── quality/               # 质量守卫与审计 Schema
│   ├── scripts/               # 工具脚本（字数统计、场景合并、敏感词扫描）
│   ├── state/                 # 状态持久化（SQLite / 向量库 / YAML）
│   ├── orchestrator.py        # 流水线编排器（核心引擎）
│   ├── pipeline.py            # 流水线配置与 LLM 注册表
│   ├── prompts.py             # Prompt 仓库加载器
│   ├── dashboard.py           # HTML Dashboard 生成器
│   ├── approval.py            # 人工审核门控
│   └── progress.py            # 进度事件发射（JSON stdout / 回调）
│
├── web/                       # Web 服务层
│   ├── server.py              # FastAPI 应用（~1300 行）
│   ├── models.py              # Pydantic 请求/响应模型
│   ├── tasks.py               # 后台任务管理器（线程池）
│   ├── novel_chat.py          # 5 步 AI 引导式创作对话
│   ├── routes/                # API 路由模块（6 个文件）
│   │   ├── projects.py        # 项目管理 / 大纲生成
│   │   ├── chapters.py        # 章节管理 / 运行 / 改写
│   │   ├── assets.py          # 素材管理 / 预设管理
│   │   ├── prompts.py         # Prompt 管理
│   │   ├── config.py          # 流水线配置 / 模型库
│   │   └── database.py        # 状态查询 / 导出 / 控制面板
│   └── frontend/              # Vue 3 SPA
│       ├── src/
│       │   ├── views/         # 13 个页面视图
│       │   ├── components/    # ~25 个可复用组件
│       │   ├── stores/        # 5 个 Pinia Store
│       │   ├── api.ts         # Axios API 客户端（60+ 端点）
│       │   ├── router.ts      # Vue Router 路由表
│       │   └── App.vue        # 主壳（侧边栏 + router-view）
│       └── dist/              # 预构建前端产物
│
├── config/                    # 全局配置模板
│   ├── pipeline.yaml          # 流水线设置（章节目标、LLM、Embedding）
│   └── models.json            # 模型库（DeepSeek V4 Flash/Pro）
│
├── assets/                    # 默认写作素材
│   ├── character_cards.yaml   # 角色卡模板
│   ├── world_bible.md         # 世界设定圣经
│   ├── style_guide.md         # 写作风格指南
│   ├── rules.yaml             # 写作规则（禁词、技法）
│   └── sensitive_words.txt    # 敏感词黑名单
│
├── prompts/                   # Agent Prompt 模板（Markdown）
│   ├── defaults/              # 默认 Prompt 副本（不可变）
│   ├── chief_editor.md        # 总编辑 Prompt
│   ├── managing_editor.md     # 执行编辑 Prompt
│   ├── planner.md             # 场景策划 Prompt
│   ├── writer.md              # 写手 Prompt
│   ├── auditor.md             # 审计员 Prompt
│   └── ...（共 15 个 Prompt 文件）
│
├── presets/                   # 体裁/类型预设
│   ├── channels/              # 频道预设（男频 / 女频 / 通用 / 自定义）
│   ├── themes/                # ~30 个主题预设（仙侠、都市、科幻、悬疑等）
│   ├── mechanisms/            # ~11 个机制预设（重生、穿越、系统、直播等）
│   ├── cool_points/           # ~13 个爽点预设（复仇、升级、打脸、求生等）
│   └── female_*/male_*/       # ~20 个预组合体裁指南
│
├── projects/                  # 多项目工作区
│   ├── default/               # 默认项目模板
│   └── {hex_id}/              # 约 20 个已有项目
│
├── state/                     # YAML 状态（兼容层）
├── workspace/                 # 生成的章节输出
├── dashboard/                 # 生成的 HTML Dashboard
├── data/                      # SQLite 数据库 + 向量存储
├── tests/                     # 7 个测试文件
├── docs/                      # 设计文档与路线图
├── scripts/                   # 外部工具脚本
└── scratch/                   # 实验性草稿
```

---

## 三、前端页面一览

| 路由 | 视图组件 | 功能说明 |
|------|---------|---------|
| `/` | `LibraryView.vue` | **项目库** — 列出所有项目，切换、创建、删除 |
| `/create` | `CreateWizard.vue` | **AI 引导创建** — 5 步对话式小说创建向导 |
| `/reader` | `ReaderView.vue` | **阅读器** — 阅读已生成章节的纯阅读视图 |
| `/control` | `ControlPlaneView.vue` | **叙事控制台** — 叙事债务、校准报告、尺度概览 |
| `/workspace` | `Dashboard.vue` | **工作台仪表盘** — 统计数据概览 |
| `/outline` | `OutlineView.vue` | **大纲编辑器** — 宏观大纲、故事弧编辑 |
| `/chapters` | `ChapterList.vue` | **章节列表** — 状态、字数、操作按钮 |
| `/chapters/:id` | `ChapterDetail.vue` | **章节详情** — 正文、场景计划、审计报告、质量报告 |
| `/state` | `StateView.vue` | **状态查看器** — 角色、事件、伏笔、钩子、物品、线索 |
| `/timeline` | `TimelineView.vue` | **时间线可视化** — 节点、关系边、伏笔、钩子 |
| `/assets` | `AssetEditor.vue` | **素材编辑器** — 角色卡、世界圣经、风格指南、规则、自定义 |
| `/logs` | `CallLogView.vue` | **调用日志** — LLM API 调用记录（Token、延迟、模型） |
| `/config` | `ConfigView.vue` | **配置中心** — LLM 设置、Embedding、运行时、模型库 |
| `/tasks` | `TaskMonitor.vue` | **任务监控** — 运行中/已完成/失败的章节任务 |

路由守卫：除 `/`、`/create`、`/config` 外，若无活跃项目则重定向到 `/library`。

---

## 四、后端 API 端点

### 项目管理 (`web/routes/projects.py`)
| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/projects` | 列出所有项目 |
| GET | `/api/projects/current` | 获取当前活跃项目 |
| POST | `/api/projects` | 创建新项目 |
| DELETE | `/api/projects/{pid}` | 删除项目 |
| POST | `/api/projects/{pid}/switch` | 切换活跃项目 |
| GET | `/api/outline` | 获取当前大纲 |
| PUT | `/api/outline` | 更新大纲 |
| POST | `/api/novel/plan` | 通过总编辑生成宏观大纲 |
| POST | `/api/novel/chapter-plan` | 从大纲生成章节队列 |
| POST | `/api/novel/run` | 运行完整小说生成 |

### 章节管理 (`web/routes/chapters.py`)
| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/chapters` | 列出所有章节（含统计） |
| GET | `/api/chapters/{id}` | 获取章节详情（正文、计划、审计、质量） |
| DELETE | `/api/chapters/{id}` | 删除章节 |
| POST | `/api/chapters/run` | 运行单章生成 |
| POST | `/api/chapters/run-batch` | 批量生成章节 |
| POST | `/api/chapters/{id}/rewrite` | 改写已有章节 |
| GET | `/api/chapters/{id}/suggest-goal` | AI 预测章节目标 |
| GET | `/api/chapters/tasks` | 列出后台任务 |
| GET | `/api/chapters/tasks/{id}` | 获取任务状态 |
| POST | `/api/novel/chat` | 5 步 AI 引导式创作对话 |
| GET | `/api/novel/chat/intro/{step}` | 获取对话步骤介绍 |

### 素材与预设 (`web/routes/assets.py`)
| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/assets` | 列出素材 |
| GET | `/api/assets/{name}` | 获取素材内容 |
| POST | `/api/assets` | 创建素材 |
| PUT | `/api/assets/{name}` | 更新素材 |
| POST | `/api/assets/generate` | AI 生成素材内容 |
| GET | `/api/presets` | 列出预设 |
| GET | `/api/presets/{id}` | 获取预设详情 |
| POST | `/api/presets` | 创建预设 |
| DELETE | `/api/presets/{id}` | 删除预设 |
| GET | `/api/presets/components/{type}/{id}` | 获取预设组件 |
| POST | `/api/presets/compose` | 组合预设组件 |

### Prompt 管理 (`web/routes/prompts.py`)
| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/prompts` | 列出所有 Prompt |
| GET | `/api/prompts/{role}` | 获取指定角色 Prompt |
| PUT | `/api/prompts/{role}` | 更新 Prompt |
| POST | `/api/prompts/{role}/reset` | 重置为默认 Prompt |

### 配置与模型 (`web/routes/config.py`)
| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/config` | 获取流水线配置（密钥脱敏） |
| PUT | `/api/config` | 更新流水线配置 |
| GET | `/api/models` | 列出模型库 |
| POST | `/api/models` | 保存模型配置 |
| DELETE | `/api/models/{id}` | 删除模型 |
| POST | `/api/models/test` | 测试模型连通性 |

### 状态与控制 (`web/routes/database.py`)
| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/state` | 获取完整小说状态 |
| GET | `/api/state/timeline` | 获取时间线数据 |
| GET | `/api/events` | 搜索事件 |
| GET | `/api/control/narrative-debt` | 叙事债务分析 |
| GET | `/api/control/calibration` | 校准报告 |
| GET | `/api/control/scale-profile` | 尺度概览 |
| GET | `/api/llm-logs` | LLM 调用日志 |
| GET | `/api/dashboard` | Dashboard HTML |
| POST | `/api/database/clear` | 清空数据库 |
| POST | `/api/export` | 导出小说（TXT / EPUB / PDF） |
| WS | `/ws/tasks` | WebSocket 实时任务推送 |

---

## 五、前端组件

| 组件 | 功能 |
|------|------|
| `AiChatGuide.vue` | 5 步 AI 引导式小说创建对话界面 |
| `ChapterAudit.vue` | 章节审计报告显示 |
| `ChapterContent.vue` | 章节正文阅读器 |
| `ChapterPlan.vue` | 章节场景计划展示 |
| `ChapterQualityReport.vue` | 质量检查报告可视化 |
| `CharacterAssetEditor.vue` | 角色卡 YAML 编辑器 |
| `CharacterCard.vue` | 单个角色卡展示 |
| `DashboardStats.vue` | 仪表盘统计网格 |
| `DataManager.vue` | 数据库管理（清空、导出） |
| `EmbeddingConfig.vue` | Embedding 提供商配置 |
| `LLMConfig.vue` | LLM 配置表单 |
| `LLMLogViewer.vue` | LLM 调用日志展示（含图表） |
| `LogStream.vue` | 实时日志流 |
| `MarkdownAssetEditor.vue` | Markdown 素材编辑器 |
| `ModelLibrary.vue` | 模型库管理界面 |
| `PresetSelector.vue` | 体裁预设选择器 |
| `PromptManager.vue` | Prompt 编辑器（按角色分 Tab） |
| `ProxyConfig.vue` | HTTP 代理配置 |
| `QuickCreateForm.vue` | 快速项目创建表单 |
| `RecentChapter.vue` | 最近章节卡片 |
| `RichEditor.vue` | 富文本编辑器 |
| `RulesAssetEditor.vue` | 写作规则 YAML 编辑器 |
| `SensitiveWordsConfig.vue` | 敏感词列表编辑器 |
| `TaskLog.vue` | 任务日志展示 |

---

## 六、后端 Agent 体系

### AI Agent（`novel_agent/agents/`）

| Agent | 类名 | 职责 |
|-------|------|------|
| base.py | `PromptAgent` / `OpenAILLM` / `StaticLLM` / `FallbackLLM` | 基础类：LLM 客户端（OpenAI 兼容、静态确定性、回退链） |
| chief_editor.py | `ChiefEditorAgent` | 生成宏观小说大纲（标题、主角、故事弧） |
| managing_editor.py | `ManagingEditorAgent` | 将故事弧拆解为单章摘要 |
| chapter_planner.py | `ChapterPlannerAgent` | 将章纲扩展为详细计划 |
| planner.py | `PlannerAgent` | 创建场景级计划（进入/退出条件、必写/禁写规则） |
| writer.py | `WriterAgent` | 写作各场景正文（场景级并行） |
| context_builder.py | `ContextBuilderAgent` | 为每个场景构建最小上下文包（向量检索） |
| length_fix.py | `LengthFixAgent` | 字数路由：短文→扩写器，长文→压缩器 |
| stitch_editor.py | `StitchEditorAgent` | 合并场景、修复衔接 |
| style_editor.py | `StyleEditorAgent` | 降低模板感，提升文笔多样性 |
| auditor.py | `AuditorAgent` | 章节审计（风险、问题、状态更新、AI味检测） |
| state_extractor.py | `StateExtractorAgent` | 从章节文本提取结构化状态 |
| chapter_summary.py | `ChapterSummaryAgent` | 生成章节摘要（含角色发展） |
| continuity_checker.py | `ContinuityCheckerAgent` | 连续性错误检查 |
| asset_compressor.py | `compress_assets()` | 压缩累积状态（归档旧线索、清除过期事件） |

### 流水线阶段（`novel_agent/phases/`）

| 文件 | 类名 | 职责 |
|------|------|------|
| base.py | `ChapterContext` | 数据类：承载章节生成的全部上下文 |
| generation.py | `GenerationPhase` | 步骤 2-5：上下文构建、场景写作、字数修正、缝合、风格编辑 |
| audit.py | `AuditPhase` | 步骤 6-10：连续性检查、状态提取、审计、质量报告、章节摘要 |
| post_audit.py | `PostAuditPhase` | 步骤 11-13：敏感词扫描、人工审批门控、状态持久化 |

---

## 七、核心生成流水线（13 步）

每章生成经过以下 13 个 Agent 顺序处理：

```
1. 总编辑 (Chief Editor)       → 生成宏观大纲（标题、主角、故事弧、主题）
2. 执行编辑 (Managing Editor)  → 将故事弧拆解为单章摘要与目标
3. 章节策划 (Chapter Planner)  → 将章纲扩展为详细章节计划
4. 场景策划 (Planner)          → 创建场景级计划（进入/退出条件、必写/禁写规则）
5. 上下文构建 (Context Builder) → 通过向量检索组装最小上下文包
6. 写手 (Writer)               → 写作各场景正文（场景级并行）
7. 字数修正 (Length Fix)       → 短文→扩写 / 长文→压缩
8. 缝合编辑 (Stitch Editor)    → 合并场景、修复衔接
9. 风格编辑 (Style Editor)     → 降低模板感、提升文笔多样性
10. 连续性检查 (Continuity Checker) → 验证叙事一致性
11. 状态提取 (State Extractor) → 提取事件、角色、伏笔、时间线
12. 审计员 (Auditor)           → QA 审计（风险等级、问题检测、AI味分析）
13. 章节摘要 (Chapter Summary) → 生成章节摘要（含角色发展弧）
```

---

## 八、前端状态管理（Pinia Stores）

| Store | 文件 | 管理内容 |
|-------|------|---------|
| `project` | `stores/project.ts` | 当前项目、项目列表、创建/切换/删除 |
| `chapter` | `stores/chapter.ts` | 章节列表、任务、当前章节详情、提交章节 |
| `config` | `stores/config.ts` | 流水线配置 |
| `state` | `stores/state.ts` | 小说连续性状态（角色、事件、伏笔、钩子、物品、线索）及时间线 |
| `tasks` | `stores/tasks.ts` | 日志条目、进度条目、轮询（2 秒间隔）、Electron IPC 桥接 |

---

## 九、数据存储机制

### 主存储：SQLite（`data/novel.sqlite`）
- WAL 日志模式，支持并发读
- 线程安全，显式锁
- 12+ 张表：

| 表名 | 存储内容 |
|------|---------|
| `events` | 章节事件（关联角色/物品/线索） |
| `objects` | 小说内物品（持有者、状态） |
| `threads` | 故事线索（标题、状态、摘要） |
| `character_state` | 角色状态（位置、情绪、完整载荷） |
| `chapters` | 章节索引（ID、标题、字数、风险等级） |
| `chapter_summaries` | 章节摘要与路径 |
| `timeline_nodes` | 时间线节点（角色、地点、组织） |
| `timeline_edges` | 节点关系边（强度、变化描述） |
| `foreshadows` | 伏笔（状态、截止章节、揭示章节） |
| `hooks` | 叙事钩子（状态、压力等级） |
| `reader_promises` | 对读者的承诺 |
| `secrets` | 故事秘密（揭示追踪） |
| `vector_embeddings` | 向量嵌入（ID、类型、文本、向量、元数据） |

### 辅助存储
- **YAML 文件**（`state/*.yaml`）— 兼容层，由 `StateManager` 保持同步
- **JSON 文件** — 每章产物：`plan.json`、`checkpoint.json`、`state_update.json`、`reports/` 下各类报告
- **向量存储** — SQLite + NumPy，回退链：智谱 AI → OpenAI → 本地 TF 骨架

---

## 十、叙事控制模块（`novel_agent/control/`）

| 模块 | 功能 |
|------|------|
| `scale_profile.py` | 6 种尺度配置（micro / short / medium / long / epic / infinite），适配不同规划模式 |
| `chapter_window.py` | 章节窗口标准化与节奏报告 |
| `calibration.py` | 大纲 vs 实际章节的校准报告 |
| `narrative_debt.py` | 叙事债务分类（伏笔、承诺、秘密）按紧急度排序 |
| `genre_genes.py` | 确保大纲中包含体裁特定的结构基因 |

---

## 十一、质量控制模块（`novel_agent/quality/`）

| 模块 | 功能 |
|------|------|
| `guard_registry.py` | 统一守卫结果注册（PASS / WARN / FAIL） |
| `audit_schema.py` | 审计 JSON Schema 校验 |
| `style_rules.py` | 反 AI 味检测（情感讲述、抽象修饰语、对话过度完整、结尾类型分析） |
| `hooks.py` | 叙事钩子分析 |
| `scene_delta.py` | 场景级变更追踪 |
| `report.py` | 完整质量报告构建器 |

---

## 十二、配置文件说明

| 文件 | 用途 |
|------|------|
| `config/pipeline.yaml` | 流水线核心配置：章节目标字数、场景目标、并行数、重试次数、LLM 路由、Embedding 配置 |
| `config/models.json` | 模型库：预定义 LLM 配置（DeepSeek V4 Flash/Pro）含 base_url、api_key、model、max_tokens、temperature、timeout、proxy |
| `projects.json` | 多项目注册表：项目 ID→名称/描述/时间戳，跟踪活跃项目 ID |
| `.env.example` | 环境变量模板：OPENAI_API_KEY、OPENAI_BASE_URL、DEEPSEEK_API_KEY、HTTP_PROXY |
| `assets/rules.yaml` | 写作规则：禁词/禁句、写作技法、参考作者 |
| `assets/sensitive_words.txt` | 敏感词黑名单（内容扫描用） |
| 项目级 `projects/{id}/config/pipeline.yaml` | 项目专属流水线配置 |
| 项目级 `projects/{id}/config/project_meta.json` | 项目元数据（体裁、频道、目标章数、尺度配置） |

---

## 十三、预设/模板系统

| 类型 | 数量 | 示例 |
|------|------|------|
| 频道 (Channels) | 4 | 男频、女频、通用、自定义 |
| 主题 (Themes) | ~30 | 仙侠、都市、科幻、悬疑、言情、历史、末日、游戏 |
| 机制 (Mechanisms) | ~11 | 重生、穿越、系统流、直播、无限流、模拟器 |
| 爽点 (Cool Points) | ~13 | 复仇、升级、打脸、求生、逆袭、称霸 |
| 预组合指南 | ~20 | female_xianxia、male_urban、male_scifi 等 |

组件可自由组合，生成写作指南应用于项目。

---

## 十四、AI 引导式创作（5 步对话）

| 步骤 | 目标 | 产出 |
|------|------|------|
| Step 1 | 从用户灵感中提取主题/体裁 | 主题定位 |
| Step 2 | 构建主角画像（欲望、缺陷、优势、限制） | 角色卡 |
| Step 3 | 识别冲突与对抗力量 | 故事张力 |
| Step 4 | AI 综合摘要卡供用户编辑 | 故事概要 |
| Step 5 | 配置尺度（章数、字数目标） | 项目参数 |

---

## 十五、尺度自适应架构

6 种尺度配置，自适应调整规划策略：

| 尺度 | 典型章数 | 规划模式 | 大纲层级 | 状态层 |
|------|---------|---------|---------|--------|
| Micro | 1-5 | 单次生成 | 无 | 热数据 |
| Short | 5-20 | 完整前置规划 | L0-L1 | 热数据 |
| Medium | 20-80 | 滚动窗口 | L0-L2 | 热+温 |
| Long | 80-200 | 动态卷 | L0-L2 | 热+温+冷 |
| Epic | 200-500 | 分形 | L0-L3 | 全层+压缩 |
| Infinite | 500+ | 容器-剧集 | L0-L3 | 全层+归档 |

---

## 十六、导出系统

| 格式 | 实现方式 |
|------|---------|
| TXT | 带标题头的纯文本导出 |
| EPUB | 通过 ebooklib 生成标准 EPUB |
| PDF | 需额外依赖 |

---

## 十七、桌面应用

- **打包方式：** Electron + PyInstaller
- **安装包：** NSIS 安装器（Windows）
- **架构：** Python 运行时 + FastAPI 后端 + Vue 前端 打包为一体
- **实时通信：** WebSocket + Electron IPC

---

## 十八、断点续传

- 每章独立 checkpoint（`checkpoint.json`）
- 记录已完成阶段，支持从 generation / audit / state_update 任意阶段恢复
- 服务重启时自动将过期的 pending/running 任务标记为 failed

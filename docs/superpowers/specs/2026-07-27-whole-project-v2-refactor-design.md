# 栖墨（INKREST）V2 全项目重构设计

- **日期：** 2026-07-27
- **状态：** 对话方案已确认，待书面复核与实施计划
- **产品定位：** 本地优先、Windows/Electron 单用户桌面应用
- **兼容策略：** 允许清空旧数据重新开始，不提供旧项目数据迁移

## 1. 背景

栖墨已经具备完整的长篇小说生产能力：项目管理、题材与大纲、人物和世界观资产、章节生成、审校、修章、状态追踪、版本、导出、模型配置、插件、Electron 桌面运行和大量自动化测试。

当前主要问题不是功能缺失，而是功能增长快于边界治理：

- 自动生产与专业写作混在同一导航和页面中；
- 页面入口、状态计算、引导流程和编辑能力重复；
- 任务管理按项目隔离，但进度与中止回调仍是进程级单例；
- Electron、插件与依赖安全边界不足；
- 部分测试依赖本地忽略目录，无法保证干净克隆可重复；
- 页面视觉、术语、设计令牌和可访问性不统一；
- 文档、代码规模描述和实际工程状态出现漂移。

本设计采用“原仓深度重构，保留成熟业务能力”的路线。不会整体改写所有生成算法，也不会为了追逐技术热点更换成 LangGraph、Temporal、Neo4j 或其他重型基础设施。

## 2. 审查基线

### 2.1 验证结果

审查时的可重复基线：

- 后端测试：748 passed，5 skipped；
- 前端单元测试：143 passed；
- 前端生产构建通过；
- 前端 bundle 预算通过：50 个 JavaScript chunk，总计 1,823,067 bytes；
- API p95 性能基线通过；
- `pip check` 无破损依赖；
- Git 工作区干净。

这些结果证明现有系统具备可重构基础，不应抛弃全部已验证行为。

### 2.2 工程规模

- `novel_agent/`：约 148 个文件、20,018 行；
- `web/`：约 329 个文件、55,547 行；
- `web/frontend/src/`：约 247 个文件、42,014 行；
- `tests/`：约 113 个文件、13,352 行；
- Vue 单文件组件：129 个。

较大的维护热点包括 `App.vue`、`ModelLibrary.vue`、`StateChronicleTab.vue`、`web/tasks.py`、`web/factory_summaries.py`、`sqlite_vector_store.py`、`history_repository.py` 和 `context_builder.py`。

### 2.3 已确认的关键缺陷

#### P0：多项目后台任务串线

`ProjectTaskRegistry` 为每个项目创建独立 `TaskManager`，但 `novel_agent.progress` 只保存一个模块级进度回调和中止回调。创建或激活另一个项目管理器时会覆盖前一个回调。

可能后果：

- 项目 A 的进度进入项目 B；
- 项目 A 的中止检查失效；
- 后台任务与 UI 状态不一致；
- 非当前项目即使仍有后台任务，也可能被删除。

V2 必须使用任务上下文路由进度事件，禁止用可覆盖的全局回调承担多项目调度。

#### P0：前端依赖漏洞

审查时 `npm audit` 发现：

- critical：3；
- high：15；
- low：1。

涉及 `concurrently`、`electron-builder`、`electron-updater`、`vite`、`axios` 及传递依赖。升级必须逐项进行，并在每组升级后执行单元测试、构建、bundle 和 Electron 打包验证。

#### P0：Electron 安全边界

当前主窗口设置 `sandbox: false`，且缺少：

- 导航白名单；
- 新窗口创建限制；
- 外部链接协议白名单；
- IPC sender/frame 验证；
- 每个 IPC 参数的运行时 schema 校验。

V2 必须遵循 Electron 官方安全清单，默认启用 renderer sandbox，并缩小 preload 暴露面。

#### P0：章节版本切换备份静默失败

章节版本激活逻辑引用未导入的 `create_chapter_snapshot`，异常被宽泛捕获，导致切换版本前的自动快照静默失效。

#### P1：测试不完全自包含

安全回归测试读取被 `.gitignore` 排除的 `electron_version/` 文件。当前机器因为遗留目录存在而通过，干净克隆中缺少该目录。

所有测试必须只依赖：

- Git 跟踪文件；
- 测试 fixture；
- 测试运行时显式创建的数据。

#### P1：Python 运行时不一致

本地审查环境仍使用 Python 3.8，CI 使用 Python 3.11。Python 3.8 已结束生命周期。V2 正式支持 Python 3.11 和 3.12，桌面 sidecar 与 CI 使用同一主版本。

## 3. 产品目标

### 3.1 双工作流

V2 同时支持两条互不干扰、共享数据内核的工作流。

#### 自动生产

面向希望系统完成规划、连续生成、审校、修复和导出的用户。

主路径：

`书库 → 新建作品 → 策划 → 生产 → 审校/修复 → 发布`

#### 专业写作

面向以手写为主、按需使用 AI 续写、改写、版本比较和质量检查的用户。

主路径：

`书库 → 新建作品 → 策划 → 正文 → 审校 → 发布`

两条路径共享：

- 项目；
- 大纲；
- 人物和世界观；
- 章节与版本；
- 事实状态；
- 任务；
- 质量报告；
- 模型与插件。

### 3.2 非目标

- 不建设云端多租户 SaaS；
- 不引入多人实时协作；
- 不兼容旧数据库和旧项目目录；
- 不复制 GPL/AGPL 项目代码；
- 不把所有功能做成可视化节点工作流；
- 不在本轮引入移动端；
- 不自动触发真实小说生成作为开发验证。

## 4. 信息架构

### 4.1 全局层

未进入项目时只展示：

- 书库；
- 新建作品；
- 全局搜索／命令面板；
- 设置；
- 扩展。

### 4.2 项目层

进入项目后，主导航固定为：

1. 概览；
2. 策划；
3. 正文；
4. 生产；
5. 发布。

运行状态显示为侧栏底部的小型指示器。异常时打开诊断抽屉，而不是常驻大卡片。

### 4.3 页面合并映射

| 现有页面或功能 | V2 去向 |
| --- | --- |
| Library、Studio Board | 书库，工作室统计作为切换视图 |
| Onboarding、SetupWizard、AppTour、FirstBookGuide、AiChatGuide | 一个渐进式首次使用流程 |
| CreateWizard、TropeWorkshop、QuickCreate | 新建作品中心 |
| Outline、Assets、State | 策划中心 |
| ChapterList、ChapterDetail、WritingWorkspace、Reader | 正文中心 |
| Dashboard、ChapterMaintenance、Monitor、TaskLog | 生产中心 |
| 平台反馈、黄金检查、导出、阅读预览 | 发布中心 |
| PluginManager | 设置 → 扩展 |
| Pet | 可关闭扩展，不进入核心导航 |

旧路由在过渡期保留重定向。对应旧组件完成替换并通过测试后删除。

## 5. 页面设计

### 5.1 应用外壳

- 侧栏宽度统一，不在页面内重复创建第二套全局导航；
- 项目名称、导航、运行状态和全局入口层级清晰；
- 所有路由切换默认回到内容区顶部；
- 子页面刷新前先完成项目 store hydration，不得错误重定向到书库；
- 支持 `Ctrl/Cmd + K` 搜索页面、章节、人物、设定和命令；
- 桌面最小宽度与缩放策略进入 E2E 测试。

### 5.2 书库

书籍卡片仅展示：

- 封面；
- 书名；
- 作者；
- 章节进度；
- 更新时间；
- 未处理风险。

导入、导出、置顶、重命名和删除进入统一菜单。工作室看板改为书库顶部的视图切换，不与书库争夺主入口。

### 5.3 新建作品

统一为四步：

1. 选择自动生产或专业写作；
2. 选择快速输入、AI 引导、导入大纲或题材模板；
3. 确认规模、平台和写作方向；
4. 创建项目骨架并进入策划中心。

灵感工坊作为第二步的题材模板，不保留独立顶级页面。

环境未就绪时只展示与当前阻断原因有关的设置，不再依次弹出多套向导。

### 5.4 策划中心

采用可调整三栏布局：

- 左侧实体树：大纲、人物、地点、组织、道具、伏笔、规则；
- 中间画布：表单、卡片大纲、关系图或时间线；
- 右侧检查器：当前实体详情、关联章节和实际剧情状态。

“人物设定”和“人物当前事实”显示在同一实体详情中，以“设定”和“当前状态”区分。资产文件路径只在高级模式展示。

关系图、思维导图和时间线统一使用 Vue Flow 的节点、边、缩放和小地图能力。

### 5.5 正文中心

使用可调整三栏：

- 左侧：卷章树；
- 中间：正文编辑器；
- 右侧：上下文、AI、审校、版本和设定。

要求：

- 中间编辑器默认占可用空间的 60% 以上；
- 左右侧栏均可折叠、调整宽度并记忆尺寸；
- 专注模式隐藏全部侧栏；
- 卷章树支持搜索、状态过滤和虚拟滚动；
- 自动保存取代突出的手动保存按钮；
- 顶部只保留章节标题、保存状态和少量一级动作；
- 平台、分支、排版、快照和历史进入菜单或检查器；
- AI 续写、改写、润色和扩写使用选区浮动菜单；
- AI 结果以 Ghost Text 或差异视图出现，用户接受后才写入；
- 版本、快照和试写分支统一为“历史记录”；
- 阅读模式成为编辑器预览。

#### 文档模型

正文主存储采用：

```text
document_id
chapter_id
title
content_json       # Tiptap JSON
plain_text         # 模型、字数与 TXT 导出投影
markdown_text      # Markdown/DOCX/EPUB 导出投影
revision
created_at
updated_at
```

每次保存使用 revision 做乐观并发控制。版本快照保存完整 `content_json` 和派生文本，不再同时依赖散落文本文件与数据库记录判断“正史”。

### 5.6 生产中心

生产中心只消费后端统一生成的 `ProjectSnapshot`。

核心摘要：

- 已完成章节；
- 已规划章节；
- 当前任务；
- 阻断原因；
- 下一步动作；
- 成本；
- 质量趋势。

内部区域：

- 自动生产队列；
- Agent 执行时间线；
- 审校与修章队列；
- 失败恢复；
- 费用；
- 日志抽屉。

不再由不同组件分别推导 `3/80`、`5/80`、`4/6`、`6/6` 等进度。

### 5.7 发布中心

- 成书阅读预览；
- 平台选择；
- 平台规则检查；
- 外站试审反馈；
- 黄金章节检查；
- TXT、Markdown、DOCX、EPUB、PDF 导出；
- 导出前检查清单。

### 5.8 设置

设置拆分为：

- 模型与提供方；
- Embedding 与记忆；
- 生成与质量；
- 写作与排版；
- 扩展；
- 系统、数据与诊断。

普通用户默认使用表单。Prompt、YAML、JSON 和插件配置的源码模式使用 CodeMirror 6，仅在高级模式显示。

## 6. 统一状态与数据契约

### 6.1 ProjectSnapshot

后端提供唯一项目快照：

```text
project
workflow_mode
readiness
outline_progress
chapter_progress
active_tasks
blocking_issues
quality_summary
cost_summary
next_actions
updated_at
```

所有状态标签通过共享枚举和本地化映射呈现，不直接向用户显示 `low`、`medium`、`missing`、`stable` 等内部值。

### 6.2 任务模型

新任务表至少包含：

```text
id
project_id
task_type
status
payload_json
result_json
attempt
max_attempts
claim_token
lease_expires_at
heartbeat_at
checkpoint
status_reason
created_at
started_at
finished_at
```

状态机：

```text
pending
claimed
running
paused
succeeded
failed
cancelled
```

原则：

- 任务类型不得再从 `goal` 字符串推断；
- claim 和 lease 保证崩溃恢复；
- heartbeat 判断失联任务；
- 相同 task id 的恢复必须幂等；
- 外部副作用必须使用幂等键；
- 进度事件带 `project_id` 和 `task_id`；
- 中止检查从当前任务上下文解析，不使用可覆盖全局回调。

### 6.3 配置模型

- Pydantic schema 是后端配置真相；
- 配置文件带 `schema_version`；
- 无效 YAML 不再静默退化为空配置；
- 配置写入使用临时文件和原子替换；
- 前端从后端 schema 生成表单元数据；
- Ajv 用于插件 JSON Schema 和前端即时校验；
- 密钥只保存在本地安全配置，不进入项目导出和日志。

### 6.4 数据真相源

| 数据 | 唯一真相源 | 其他表示 |
| --- | --- | --- |
| 项目、故事实体、章节顺序、任务、质量结果 | SQLite | API DTO、缓存与界面投影 |
| 正文 | SQLite 中的 Tiptap JSON 文档 | `plain_text`、Markdown 与导出文件 |
| 模型、生成、质量和应用设置 | 带版本的配置 schema | 设置表单与高级源码视图 |
| Prompt 与预设模板 | Git 跟踪的资源文件 | 运行时只读加载与用户覆盖层 |
| 日志与诊断包 | 结构化运行时日志 | 界面筛选视图与用户主动导出的诊断包 |
| TXT、Markdown、DOCX、EPUB、PDF | 不是真相源 | 从数据库和配置按需生成的产物 |

同一业务数据不得同时由 SQLite、YAML、Markdown 和内存 store 分别维护。前端 store 只是服务端状态的缓存；写入成功必须以服务端返回的新 revision 为准。

### 6.5 V2 数据切换

用户已批准清空旧数据重新开始，因此 V2 不实现旧 schema 和旧项目目录的迁移器，也不保留长期兼容读写层。

切换仍必须是显式且可审计的：

1. V2 启动时识别旧 schema 或旧目录版本；
2. 提供“导出旧目录备份”和“清空并初始化 V2”两个动作；
3. 未经一次明确确认，不静默删除现有用户文件；
4. 清空操作只作用于解析并校验过的项目运行时目录，不作用于仓库、用户主目录或外部路径；
5. 初始化完成后写入 V2 schema/version 标记；
6. 开发和自动化测试使用临时目录及显式 reset fixture，不依赖开发者机器上的残留数据。

## 7. 前端架构

```text
src/
  app/
    router/
    shell/
    bootstrap/
  features/
    library/
    creation/
    planning/
    manuscript/
    production/
    publishing/
    settings/
  entities/
    project/
    document/
    chapter/
    story-entity/
    task/
  shared/
    api/
    ui/
    editor/
    graph/
    schema/
    styles/
```

约束：

- 页面不得直接散落调用 Axios；
- API 使用明确 DTO，不使用跨边界 `any`；
- 每个功能模块有 service、store/composable、view 和测试；
- 共享组件不得包含业务请求；
- `App.vue` 只承担启动和外壳装配；
- 页面级 CSS 不再大量覆盖 Element Plus；
- Emoji 不作为正式功能图标；
- 所有颜色、间距、圆角、字体和阴影来自设计令牌；
- 一个页面只允许一个主 `main` landmark；
- 交互控件必须有可访问名称和键盘行为。

## 8. 可复用组件决策

| 项目 | 用途 | 许可证/策略 |
| --- | --- | --- |
| [Tiptap](https://github.com/ueberdosis/tiptap) | 正文编辑器、选区命令、自定义节点 | 使用 MIT 开源核心 |
| [Splitpanes](https://github.com/antoniandre/splitpanes) | 可调整、可折叠三栏布局 | MIT，采用 |
| [Vue Flow](https://github.com/bcakmakoglu/vue-flow) | 大纲、关系图、时间线 | MIT，采用 |
| [TanStack Virtual](https://github.com/TanStack/virtual) | 章节、任务和日志虚拟滚动 | MIT，采用 |
| [TanStack Table](https://github.com/TanStack/table) | 复杂列表的排序、筛选、选择 | MIT，按需采用 |
| [CodeMirror 6](https://github.com/codemirror/dev) | Prompt、YAML、JSON 源码编辑 | MIT，采用 |
| [Ajv](https://github.com/ajv-validator/ajv) | JSON Schema 校验 | MIT，采用 |
| [Element Plus](https://github.com/element-plus/element-plus) | 基础表单、弹窗和控件 | 保留并封装 |

社区应用只用于产品和交互参考：

- [Author](https://github.com/YuanShiJiLoong/author)：AGPL-3.0，不复制代码；
- [Manuskript](https://github.com/olivierkes/manuskript)：GPL-3.0，不复制代码；
- [302 AI Novel Writing](https://github.com/302ai/302_novel_writing)：Apache-2.0，但技术栈不同，以交互参考为主；
- [Cherry Studio](https://github.com/CherryHQ/cherry-studio)：参考模型管理交互，不直接引入其代码。

不采用：

- 完整 Tailwind/Shadcn 迁移；
- JSON Forms Vue 作为核心表单渲染器；
- Monaco 作为普通配置编辑器；
- 通用 BPMN 工作流设计器；
- Tiptap 付费云功能。

## 9. Electron 与插件

### 9.1 Electron

- 删除旧 Express/SQLite Electron 服务；
- 删除未使用 `main.cjs`；
- 删除未使用章节直连 CLI IPC；
- renderer 启用 sandbox；
- 限制导航和窗口创建；
- 外部链接仅允许 `https:` 和明确白名单；
- IPC 校验 sender/frame；
- IPC 参数使用 schema 校验；
- preload 只暴露最小能力；
- 后端启动、停止和重启使用明确状态机；
- 停止后等待进程退出，再进行重启；
- 打包只包含当前构建入口。

### 9.2 插件

当前 subprocess 只能称为“进程隔离”，不能称为安全沙箱。

V2：

- 将 `plugin_sandbox` 重命名为 `plugin_process_isolation`；
- 能力声明进入安装确认和运行时授权；
- 默认禁止本地插件；
- Web 插件只能注册受控扩展点，不允许任意挂载全局路由；
- 超时进程必须可终止；
- 文件和网络访问通过宿主 broker；
- 插件错误不得破坏核心流水线；
- 插件目录、配置和日志独立。

## 10. 删除清单

第一批确定删除候选：

- `web/frontend/electron/main.cjs`；
- `web/frontend/electron/server/`；
- `web/frontend/electron/database/`；
- `scripts/_patch_orchestrator_delegate.py`；
- `scripts/_extract_novel_batch.py`；
- `scripts/_trim_audit_sync_rewrite.py`；
- 未被 renderer 调用的章节直连 IPC；
- 仅为旧数据格式存在的兼容层；
- 重复正文 textarea 编辑器；
- 重复 onboarding 和首次引导组件；
- 被新策划、正文、生产中心替代的旧页面组件。

删除条件：

1. `rg`、路由、构建入口和测试证明无活动引用；
2. 替代路径已经通过测试；
3. 删除后完整测试和打包通过；
4. 文档同步更新。

## 11. 测试与质量门禁

### 11.1 后端

- 单元测试；
- API 合约测试；
- SQLite schema 和事务测试；
- 任务状态机属性测试；
- 崩溃恢复、租约过期和幂等测试；
- 多项目并发进度路由测试；
- 插件隔离与权限测试；
- 性能基线。

### 11.2 前端

- Vitest 单元测试；
- API DTO/adapter 测试；
- 路由 hydration 和 scroll 测试；
- Tiptap 文档投影测试；
- Playwright 关键流程测试；
- 关键页面截图回归；
- `@axe-core/playwright` 无障碍检查；
- 键盘导航测试；
- 长章节、长日志虚拟列表性能测试；
- bundle 预算。

### 11.3 桌面

- Electron 主进程单元测试；
- IPC sender 和参数校验测试；
- 后端崩溃恢复测试；
- 安装、便携包、升级和卸载测试；
- 干净 Windows 环境首次启动；
- bundle manifest 验证。

### 11.4 CI

新增门禁：

- Ruff；
- Python 3.11 与 3.12 测试矩阵；
- Python 类型检查的渐进式基线；
- ESLint；
- Vue TypeScript 检查；
- npm audit 严重级别门禁；
- 许可证清单；
- 干净克隆构建；
- 视觉回归；
- 打包 smoke。

## 12. 实施阶段

### Phase 0：工程与安全基线

- 修复已确认缺陷；
- 引入 lint、格式化、安全审计；
- 升级高危依赖；
- 固定 Python 3.11/3.12；
- 删除确定无用代码；
- 建立干净克隆门禁。

### Phase 1：状态、配置与任务内核

- 新 SQLite schema；
- `ProjectSnapshot`；
- 配置 schema；
- 新任务状态机；
- 多项目事件路由；
- 幂等与恢复。

### Phase 2：应用外壳与设计系统

- 新目录结构；
- 新导航；
- 统一术语和图标；
- 统一页面骨架、按钮、表格、空状态和错误状态；
- 路由 hydration、scroll 和命令面板。

### Phase 3：新建作品与策划中心

- 合并 onboarding；
- 合并创建流程；
- 故事实体统一模型；
- 大纲、人物、世界观、状态和关系图。

### Phase 4：正文中心

- Tiptap 文档模型；
- 三栏布局；
- 自动保存；
- AI 差异接受；
- 历史与版本；
- 阅读预览。

### Phase 5：生产中心

- 自动生产队列；
- 任务与 Agent 时间线；
- 统一质量与修章；
- 日志和费用；
- 故障恢复 UI。

### Phase 6：发布、设置、插件与 Electron

- 发布中心；
- 新设置结构；
- 插件权限；
- Electron 安全；
- 打包链路。

### Phase 7：旧代码移除与最终验收

- 删除旧页面、路由、API 和兼容层；
- 更新全部文档；
- 执行干净安装；
- 完成全量回归、性能和打包验收。

## 13. 验收标准

### 功能

- 两条工作流均可从新建项目完成到导出；
- 自动生产与专业写作入口和状态互不混淆；
- 所有现有核心能力有明确新归属；
- 无重复任务、进度、版本和质量真相源。

### 可靠性

- 后端、前端、E2E 和桌面测试全部通过；
- 任务在进程重启后可恢复或明确失败；
- 多项目任务不会串进度或中止信号；
- 项目不能在活跃任务期间被错误删除；
- 配置错误不会静默退化。

### 体验

- 项目主导航不超过 5 项；
- 正文编辑器默认占主要工作区；
- 普通用户界面不显示内部状态码和文件路径；
- 页面切换滚动正确；
- 核心流程支持键盘；
- 关键页面通过自动无障碍检查；
- 视觉回归覆盖书库、策划、正文、生产、发布和设置。

### 性能

- API p95 不低于现有基线；
- 首屏和路由 chunk 受 bundle 预算约束；
- 1000 章节和大量日志使用虚拟滚动；
- 空闲时不持续进行无意义轮询；
- Electron 后端重启不产生重复进程。

## 14. 实施约束

- 所有行为变更先写失败测试；
- 每个阶段结束时系统必须可运行；
- 删除动作必须由引用检查和测试证明；
- 不触发真实模型小说生成，除非用户单独批准；
- 不提交 API Key、`.env`、本地模型配置和项目数据；
- 保持 `workspace/`、`projects/`、`state/`、`data/`、`logs/` 和打包产物为运行时数据；
- 大改动采用小提交，确保可定位和回滚。

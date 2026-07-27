# V2 Phase 6：发布中心、设置、插件权限与桌面安全重构计划

> 日期：2026-07-27  
> 分支：`codex/v2-refactor`  
> 范围：规范化成书导出、发布工作区、设置收敛、插件权限边界、Electron 安全与 Windows 打包链路。

## 目标

把当前分散且相互绕过的阅读预览、平台选择、黄金三章、外站反馈、试审复制和五种文件导出统一成一个发布中心，并完成桌面应用最后一组高风险边界的收口：

1. SQLite `documents` 是正文唯一真源；阅读、试审和所有导出均不得直接把 `workspace/chapters` 当作业务真相；
2. `/publishing` 同时承载成书预览、平台规则、外站反馈、黄金章节和导出预检，不再让用户跨多个隐藏入口拼接流程；
3. TXT、Markdown、DOCX、EPUB、PDF 在开发环境和打包后的 Windows 应用中使用同一套导出服务；
4. 设置按用户任务分组，普通模式只呈现表单和诊断，高级源码编辑不与常用项混排；
5. 本地插件在导入 Python 代码前展示来源和所需权限，只有用户明确确认后才建立信任；
6. Electron 所有窗口、IPC、导航、外链、权限和后端子进程遵守最小权限原则；
7. 自动化验收不触发小说生成、审校、重写或任何模型请求。

## 当前审计结论

- `/api/export`、`/api/chapters/export-trial`、旧阅读器和四个 exporter 分别读取 `chapter_final.txt` 与 `plan.json`，与 Phase 4 已建立的 SQLite 文稿真源冲突；
- TXT、EPUB、PDF、Markdown、DOCX 重复实现章节收集、排序、标题拼装和空正文判断，错误口径不一致；
- EPUB 和 PDF 通过运行时动态导入可选依赖，PyInstaller 未显式收集；桌面包中即使页面展示格式可用，实际导出仍可能失败；
- PDF 依赖系统字体扫描，缺少字体时回退 Helvetica，无法可靠显示中文；
- `capabilities` 虽已出现在插件清单中，但只做字符串透传，没有许可枚举、默认权限、信任摘要和运行时约束；启用未信任插件会隐式把“启用”当“信任”；
- Electron 已启用 `contextIsolation`、renderer sandbox、导航限制、权限拒绝和部分 IPC sender 校验，但还需要覆盖全局 sandbox、所有会话、单实例与后端子进程生命周期，并用测试固定边界；
- 设置页已有折叠区，但仍以实现模块而非用户任务组织，扩展入口和部分内部配置重复。

## 社区项目与依赖决策

- [python-docx](https://github.com/python-openxml/python-docx)：MIT，继续用于 DOCX；不重新实现 OOXML。
- [ReportLab](https://docs.reportlab.com/reportlab/userguide/ch3_fonts/)：使用其 `UnicodeCIDFont` 和简洁文档流生成 PDF；将 ReportLab 作为桌面发布能力的正式依赖并显式打包。
- [EbookLib](https://github.com/aerkalov/ebooklib)：功能成熟但为 AGPL-3.0，本项目不把它引入默认桌面分发。
- [EPUB 3.3](https://www.w3.org/TR/epub-33/) 与 [EPUBCheck](https://github.com/w3c/epubcheck)：按规范用 Python 标准库生成最小 EPUB 3 包；测试校验 mimetype、container、OPF、nav、spine 和 XHTML。EPUBCheck 是 Java 工具，不作为桌面运行时依赖。
- [Pandoc](https://github.com/jgm/pandoc)：转换能力全面，但引入大型原生二进制与额外安装/升级链路；本阶段不采用。
- [Electron 安全清单](https://www.electronjs.org/docs/latest/tutorial/security)：逐项覆盖 sandbox、context isolation、权限、导航、窗口、外链、IPC sender 与 preload 暴露面。

## 非目标与安全边界

- 本阶段不清空用户数据；旧数据切换与 V2 初始化只在 Phase 7 通过用户已授权的项目级重置流程执行；
- 不把 W3C EPUBCheck、Pandoc、Office、浏览器或系统字体变成运行前置条件；
- 不允许插件在未信任状态下被导入，也不把“启用开关”隐式解释为授予新权限；
- 不承诺 Python 插件进程内的完整操作系统级沙箱；UI 必须明确说明已信任插件会在本机进程中运行代码；
- 不自动安装、下载或更新第三方插件；
- 不自动发起平台投稿，不保存平台账号或密钥；
- 不在测试或页面加载时触发生成、外审、审校、重写和批量任务。

## 实施清单

### 任务 1：建立规范化发布领域与导出服务

- [ ] 新增 `PublicationBook`、`PublicationChapter`、`ExportPreflight`、`PublishingWorkspace` 等稳定领域契约；
- [ ] 增加一次性从 `documents` 按章节顺序收集正文的 repository/service API，空正文、筛选、标题、字数和顺序只在这里判定；
- [ ] 所有 exporter 只接收规范化 `PublicationBook`，不得自行读取项目目录；
- [ ] TXT、Markdown、试审文本使用统一标题和章节分隔规则；
- [ ] DOCX 使用 `python-docx`，对书名、章节标题和正文设置稳定样式；
- [ ] EPUB 使用 `zipfile` 生成 EPUB 3.3 最小合规结构，转义所有标题与正文；
- [ ] PDF 使用 ReportLab `UnicodeCIDFont("STSong-Light")`，分页、标题和段落均支持中文；
- [ ] 导出文件名做跨平台清洗，临时文件在响应结束后删除，错误不暴露本地绝对路径；
- [ ] 保留 `/api/export` 和试审接口作为兼容入口，但内部必须调用同一服务。

### 任务 2：建立发布工作区 API 与预检清单

- [ ] 新增 `/api/publishing/workspace`，返回项目快照、书稿目录、选中正文、平台、规则检查、黄金章节、外站反馈、导出格式和预检结果；
- [ ] 平台 profile 转成稳定 DTO，不直接泄漏内部 prompt 文本或未本地化代码；
- [ ] 预检至少覆盖：无正文、空章节、阻断审校、前三章缺失、标题缺失、平台未选择和格式不可用；
- [ ] `blocking` 与 `warning` 分离；阻断项禁止导出，警告项可由用户确认后继续；
- [ ] 平台更新、外站反馈保存后返回新的工作区/稳定 revision，前端不自行推断；
- [ ] 项目之间的正文、反馈、平台和导出范围严格隔离。

### 任务 3：重构统一发布中心

- [ ] 新增 `/publishing`，页面顶部只展示总字数、有效章节、平台和预检状态；
- [ ] 主工作区包含“成书预览 / 平台与反馈 / 导出”三个任务页签；
- [ ] 预览使用规范化文稿 DTO，保留目录、字号、行距、版心与主题设置，不再调用旧章节文件 API；
- [ ] 平台页集中呈现平台选择、规则摘要、黄金章节检查和外站读者反馈；
- [ ] 导出页显示范围、格式、书名、文件说明和预检清单，下载前提供明确确认；
- [ ] `/reader` 兼容重定向到 `/publishing`；删除不再引用的旧 reader/export 逻辑；
- [ ] 1440×900、1100×720 及明暗主题下无横向溢出，目录与正文可独立滚动。

### 任务 4：收敛设置与扩展入口

- [ ] 设置导航改为“模型与提供方 / 记忆 / 生成与质量 / 写作与排版 / 扩展 / 系统与数据”；
- [ ] 合并重复的模型、LLM 路由与引擎就绪提示，保留单一配置写入口；
- [ ] 普通模式不展示 Prompt/YAML/JSON 源码或内部字段；现有高级编辑入口增加明确标识和风险说明；
- [ ] 扩展区显示插件安全摘要并链接统一插件管理页，不在设置中复制插件列表；
- [ ] 系统与数据区集中放置外观、诊断、运行环境和 Phase 7 数据工具入口；
- [ ] 删除硬编码说明、过时备份承诺和无实际行为的表单项。

### 任务 5：建立插件权限与信任契约

- [ ] 定义受支持的权限枚举、用户标签、风险等级与每种 `plugin_type` 的最小默认权限；
- [ ] 清单拒绝未知、重复、类型错误的权限；旧清单根据类型推导最小权限并标记为兼容模式；
- [ ] catalog 返回声明权限、有效权限、风险摘要、来源、信任状态和是否需要重新授权；
- [ ] 信任 API 必须带回用户确认的清单摘要/digest；插件包或权限变化后旧信任自动失效；
- [ ] 启用未信任插件返回冲突，不再自动建立信任；
- [ ] Web extension 和高风险能力继续受核心策略限制；未授予的能力不得注册；
- [ ] 插件页先展示权限确认对话框，再执行信任；启用、删除、更新配置均有准确影响说明；
- [ ] 更新插件作者模板与文档，给出现代清单示例和兼容策略。

### 任务 6：完成 Electron 与后端进程安全收口

- [ ] 应用启动时启用全局 renderer sandbox；全部窗口保持 `nodeIntegration: false`、`contextIsolation: true`、`sandbox: true`；
- [ ] 默认 session 与窗口 session 均拒绝权限请求，并拒绝 webview、未知导航和未知新窗口；
- [ ] 外链仅允许显式 HTTPS host allowlist，所有 IPC handler 校验 sender URL 和输入 schema；
- [ ] preload 只暴露逐项包装的方法，不暴露原始 `ipcRenderer` 或任意 channel；
- [ ] 建立单实例锁；第二实例只聚焦主窗口，不创建第二个后端；
- [ ] `PythonBridge` 的 start/restart/stop 幂等，watchdog 不得并发拉起，退出时等待精确子进程结束；
- [ ] 后端状态 IPC 返回最小稳定 DTO，不暴露命令、环境变量或本地敏感路径；
- [ ] 安全单测覆盖 URL 绕过、credential、route、sender、权限、重复启动和进程恢复。

### 任务 7：修复生产依赖与 Windows 打包链路

- [ ] 将 `python-docx`、ReportLab 及其必要运行依赖固定到生产 requirements/lock；
- [ ] 移除 EbookLib 运行时依赖与旧动态导入；
- [ ] PyInstaller 显式收集 DOCX、ReportLab、FastAPI 和项目导出模块所需资源；
- [ ] bundle 检查验证后端运行目录和五种导出能力均被包含；
- [ ] Electron 打包后启动后端、打开发布中心并导出小型中文样稿；
- [ ] 打包产物不包含 `.env`、本地模型密钥、项目数据库、工作目录和测试日志。

### 任务 8：确定性夹具与自动化验收

- [ ] 构建三个 SQLite 文稿章节的临时项目夹具，磁盘投影故意留空或写入相反内容，证明数据库为真源；
- [ ] 后端测试覆盖五种格式、筛选顺序、中文、HTML/XML 转义、空正文、损坏输入、项目隔离和临时文件清理；
- [ ] DOCX 用 `python-docx` 回读，EPUB 解包验证，PDF 检查有效页与中文内容资源；
- [ ] 前端单测覆盖发布 DTO、预检、平台/反馈、下载确认、路由兼容和插件权限确认；
- [ ] Electron 单测覆盖安全边界与进程幂等；
- [ ] Playwright 覆盖成书预览、目录切换、平台选择、反馈、预检阻断、五格式下载请求和设置/插件流；禁止真实生成；
- [ ] 浏览器手工检查发布、设置、插件在 1440×900、1100×720、明暗主题下的布局、键盘与错误态；
- [ ] 运行完整后端、前端、Electron、E2E、生产构建、bundle、依赖审计和 Windows 打包验证。

## 建议提交顺序

1. `docs: plan v2 phase 6 publishing settings and desktop`
2. `feat: make sqlite manuscripts the publishing source`
3. `feat: build unified publishing center`
4. `refactor: simplify settings and plugin management`
5. `security: enforce plugin permission grants`
6. `security: harden electron lifecycle and ipc`
7. `build: package publishing dependencies`
8. `docs: record phase 6 verification`

## 完成标准

- 用户可在一个发布中心完成成书预览、平台检查、黄金章节、外站反馈和五种文件导出；
- 旧文件投影与 SQLite 内容不一致时，预览和所有导出始终使用 SQLite；
- 五种格式在开发环境和 Windows 打包产物中均可生成并被自动化回读验证；
- 设置按用户任务组织，内部配置只在高级模式出现；
- 未信任插件不会被导入，权限或包内容变化会要求重新确认；
- Electron 不接受未知权限、导航、外链或 IPC sender，重启后端不会产生重复进程；
- 页面无横向溢出、明暗主题一致、无真实模型调用；
- 全量测试、构建、bundle、依赖审计和打包验证通过。

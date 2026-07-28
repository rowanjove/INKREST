# 山山桌宠助手设计

## 目标

把山山做成小说生成 Agent 的默认内置桌宠助手。第一阶段不追求完整 AI 客服，而是先完成一个稳定、轻量、可关闭的桌宠入口：她常驻右下角，能展示当前软件状态，能在任务开始、完成、失败时切换表现，并能通过气泡把用户带到任务监控、日志、配置等页面。

核心判断：功能内置，角色资源可替换。山山默认随项目提供，但不要把桌宠系统本身做成外部插件。桌宠需要 Electron 多窗口、IPC、任务状态、路由跳转、后端健康等核心能力，第一版插件化会增加大量边界成本。资源层保留插件化形态，后续可以换角色包。

## 范围

本设计覆盖 V0.1 和 V0.2。

V0.1 是桌宠壳子：

- 独立透明 `PetWindow`，右下角显示山山。
- 可拖动，窗口位置持久化。
- 单击打开气泡窗口。
- 双击打开主窗口。
- 右键菜单提供打开主界面、隐藏山山、退出应用。
- 设置中提供启用/禁用、启动时显示、总在最前、尺寸选项。

V0.2 是状态联动：

- 根据任务状态切换 `idle`、`working`、`success`、`error`、`offline`。
- 气泡显示当前项目、运行任务、最近错误、快捷操作。
- 任务完成或失败时可主动弹出轻提示。
- 快捷操作只做低风险导航：打开任务监控、打开日志、打开配置、打开主界面。

不在本阶段实现：

- 大模型聊天。
- 自动修改配置。
- 自动重试任务。
- 清空缓存、删除项目等危险操作。
- Live2D、Spine、复杂表情差分。
- 外部第三方桌宠插件加载。

## 默认还是插件

山山应默认内置，但用户可关闭。

默认启用的理由：

- 项目页面多、任务多、配置多，右下角状态入口能降低使用门槛。
- 山山是“软件状态可视化入口”，不是单纯装饰。
- 当前项目已有 Electron 主进程、托盘、Vue 路由、Pinia stores 和任务状态轮询，内置实现最短。

可关闭的理由：

- `alwaysOnTop` 窗口可能打扰用户。
- 部分用户只想使用主窗口，不需要桌宠。
- 透明窗口和鼠标区域在不同 Windows 环境中可能有边缘问题。

插件化预留只放在资源层：

```txt
web/frontend/src/assets/pet/
├── shanshan/
│   ├── pet.json
│   ├── static/
│   ├── animations/
│   └── ui/
└── custom/
```

`pet.json` 描述角色包：

```json
{
  "id": "shanshan",
  "name": "山山",
  "default": true,
  "states": {
    "idle": "animations/idle_sheet.webp",
    "working": "animations/working_sheet.webp",
    "success": "animations/success_sheet.webp",
    "error": "animations/error_sheet.webp"
  }
}
```

## 架构

Electron 负责窗口生命周期和系统级能力：

- 主窗口：现有 Vue 应用。
- `PetWindow`：透明无边框小窗口，只显示山山。
- `BubbleWindow`：气泡和快捷操作。
- IPC：处理拖动、显示/隐藏、打开主窗口、打开页面、读取/保存桌宠设置。

Vue 负责桌宠 UI 和状态展示：

- `/pet` 路由渲染桌宠本体。
- `/pet-bubble` 路由渲染气泡面板。
- `pet` store 维护桌宠状态、设置、最近任务摘要。
- `PetSprite` 读取角色包 manifest 并播放 WebP sprite sheet。

FastAPI 第一阶段不新增复杂 Assistant 模块，只暴露或复用已有状态 API。必要时加一个轻量上下文接口，用于气泡展示聚合状态：

```txt
GET /api/assistant/context
```

该接口只返回状态摘要，不调用大模型。

## 前端文件设计

新增：

```txt
web/frontend/src/assets/pet/shanshan/
web/frontend/src/views/PetView.vue
web/frontend/src/views/PetBubbleView.vue
web/frontend/src/components/pet/PetSprite.vue
web/frontend/src/components/pet/PetStatusCard.vue
web/frontend/src/stores/pet.ts
```

修改：

```txt
web/frontend/src/router.ts
web/frontend/src/electron.d.ts
web/frontend/src/api.ts
```

`PetView.vue` 只负责桌宠本体，不承载聊天框。它处理点击、双击、右键、拖动手势，并通过 preload 暴露的 Electron API 调用主进程。

`PetBubbleView.vue` 负责状态气泡。它展示：

- 山山头像。
- 当前项目名称。
- 当前运行状态。
- 最近失败任务摘要。
- 快捷按钮：任务监控、日志、配置、主界面。

`pet.ts` store 负责：

- 桌宠启用状态。
- 当前动画状态。
- 最近一次任务状态。
- 气泡是否打开。
- 从任务 store 或 assistant context 同步状态。

## Electron 文件设计

新增：

```txt
web/frontend/electron/windows/pet-window.ts
web/frontend/electron/windows/bubble-window.ts
web/frontend/electron/ipc/pet-ipc.ts
web/frontend/electron/pet-settings.ts
```

修改：

```txt
web/frontend/electron/main.ts
web/frontend/electron/preload.ts
web/frontend/electron/tray/tray-manager.ts
```

`pet-window.ts` 创建透明窗口：

- 默认 `220x220`。
- `frame: false`。
- `transparent: true`。
- `alwaysOnTop` 根据设置决定。
- `skipTaskbar: true`。
- `hasShadow: false`。
- dev 加载 `http://localhost:5173/pet`。
- production 加载后端托管的 `/pet` 路由。

`bubble-window.ts` 创建气泡窗口：

- 默认 `420x560`。
- 位于宠物左上方。
- 不抢主窗口焦点。
- 可由宠物单击打开/关闭。

`pet-ipc.ts` 提供：

- `pet:getSettings`
- `pet:updateSettings`
- `pet:show`
- `pet:hide`
- `pet:toggleBubble`
- `pet:moveBy`
- `pet:openMain`
- `pet:navigateMain`

## 后端文件设计

V0.2 可新增轻量路由：

```txt
web/routes/assistant.py
```

修改：

```txt
web/app.py 或当前统一注册 routes 的位置
web/server.py 兼容 re-export
```

`GET /api/assistant/context` 返回：

```json
{
  "backend_health": "ok",
  "active_project": {
    "id": "project-id",
    "name": "项目名"
  },
  "running_tasks": [],
  "failed_tasks": [
    {
      "id": "task-id",
      "chapter_id": "chapter-id",
      "error": "LLM API 429 rate limit"
    }
  ],
  "recent_logs": []
}
```

实现策略应优先复用现有 project/task/log/config 能力，不在本阶段建立知识库或 LLM 调用链。

## 交互规则

桌宠窗口：

- 单击：打开或关闭气泡。
- 双击：显示主窗口并聚焦。
- 长按拖动：移动宠物窗口，超过 5px 才判定为拖动。
- 右键：打开上下文菜单。
- 透明区域不应阻挡用户鼠标，第一版通过尽量小的窗口和 `pointer-events` 控制解决。

气泡窗口：

- 位于宠物左上方，避免贴右下角时超出屏幕。
- 点击快捷按钮后关闭或保持，按行为决定。
- 点击“查看日志”导航主窗口到 `/logs`。
- 点击“任务监控”导航主窗口到 `/monitor?tab=tasks`。
- 点击“配置”导航主窗口到 `/config`。

主动提醒：

- 任务开始：切换 `working`，不弹气泡。
- 任务完成：切换 `success`，可短暂弹轻提示。
- 任务失败：切换 `error`，弹出诊断入口气泡。
- 后端断开：切换 `offline`，气泡提示后端状态异常。

## 设置

桌宠设置建议保存在 Electron `app.getPath("userData")` 下的 JSON 文件，避免污染业务配置。

字段：

```json
{
  "enabled": true,
  "showOnStartup": true,
  "alwaysOnTop": true,
  "size": 180,
  "position": {
    "x": 1200,
    "y": 760
  },
  "notifyOnTaskComplete": true,
  "notifyOnTaskError": true,
  "petId": "shanshan"
}
```

设置 UI 可以先放在现有配置页的一个“桌宠助手”分组，后续再独立成页面。

## 状态映射

```txt
无项目 / 空闲       -> idle
任务运行中          -> working
任务完成            -> success
任务失败            -> error
后端不可用          -> offline
用户拖动            -> dragging
```

当前山山资源已有：

```txt
D:\path\to\novel-agent\山山
```

实施时应复制到：

```txt
web/frontend/src/assets/pet/shanshan/
```

其中 `expressions/working/success/error` 当前是占位图。第一版接受这种限制，用位移动画和气泡文案表达状态。后续如要增强表现，再单独生成差分图。

## 错误处理

- 桌宠资源缺失：回退到 `static/idle_256.png`，并在控制台输出错误。
- WebP 动画加载失败：回退静态 PNG。
- 后端 context 请求失败：显示 `offline`，气泡显示“后端状态暂不可用”。
- 主窗口不存在：重新创建主窗口后导航。
- 宠物窗口位置超出屏幕：启动时夹到当前 workArea 内。
- 设置文件损坏：重建默认设置并保留损坏文件为 `.bak`。

## 测试策略

单元测试：

- `pet-settings.ts` 读写默认值、损坏文件回退、位置夹取。
- `pet.ts` store 状态映射。
- assistant context 后端接口的空项目、运行任务、失败任务场景。

前端测试：

- `PetSprite` 在 WebP 不可用时回退 PNG。
- `PetBubbleView` 按 context 显示正确按钮。

手工 / 浏览器验证：

- dev 模式能打开 `/pet` 和 `/pet-bubble`。
- 宠物窗口透明、无边框、不进任务栏。
- 单击、双击、拖动、右键行为不冲突。
- 任务运行、完成、失败时状态切换。
- 打包后资源路径正确。

## 后续演进

V0.3：AI 问答。

- 增加 `/api/assistant/chat`。
- 收集当前页面、任务、日志、配置。
- 引入软件使用手册和错误手册。
- 返回回答和建议操作按钮。

V0.4：诊断和低风险修复。

- 增加规则诊断。
- 支持测试模型连通性、打开配置、重试失败任务。
- 中高风险操作必须确认。

V0.5：角色资源包。

- 支持多个内置角色。
- 支持用户导入角色包。
- 角色包只影响资源和文案，不允许直接执行代码。

## 决策记录

- 山山默认内置，不做外部插件。
- 桌宠系统是核心应用能力，资源包才是可替换层。
- 第一阶段不接 LLM，先把窗口、状态、提醒、导航做稳。
- 第一阶段不做危险操作，快捷按钮只导航。
- 使用 WebP sprite sheet 和静态 PNG，不引入 Live2D/Spine。

# 栖墨 · INKREST 品牌升级设计

## 目标

将软件主品牌从 `NovelAgent` 升级为：

- 中文主名：`栖墨`
- 英文副名：`INKREST`
- 中文介绍句：`一方安放灵感与长篇故事的智能写作空间。`

本次升级只调整软件主品牌，不改变产品功能，不修改小说项目数据，也不改变内置助手山山的名称与形象。

## 品牌定位

栖墨是一款面向长篇创作的智能写作空间。品牌气质应文雅、安静、有书卷气，减少工具平台常见的冰冷技术感。

“栖”代表安放、沉静与长期停留，“墨”代表书写、故事与创作。英文副名 `INKREST` 由 `ink` 与 `rest` 组成，用于安装包、桌面快捷方式和技术标识。

## 图标设计

采用已确认的 `栖墨 · INKREST` 图标方案：

- 外形：圆角方形桌面应用图标。
- 主体：左右展开的书页，形成安静的栖所。
- 中心：暖金色微光，表达灵感落笔的时刻。
- 配色：深墨蓝、米白纸页、暖金点缀。
- 边界：不使用山山形象，不使用人物形象，不将内置助手与软件主品牌混合。

桌面候选源文件位于：

`D:\design-assets\品牌候选方案\01-栖墨\icon.svg`

实施时从 SVG 导出：

- `web/frontend/public/favicon.svg`
- `web/frontend/build/icon.png`
- `web/frontend/build/icon.ico`

## 名称呈现

### 主界面

侧栏品牌区域使用：

- 主标题：`栖墨`
- 副标题：`INKREST · 智能长篇写作空间`

### 网页与桌面端

- 网页标题：`栖墨 · INKREST`
- Electron 窗口标题：`栖墨 · INKREST`
- Electron 应用名：`栖墨`
- 安装包产品名：`栖墨`
- 托盘提示：`栖墨 · INKREST - 智能长篇写作空间`
- 退出菜单：`退出栖墨`
- 更新提示：`栖墨 <版本号> 已发布`
- 远程访问令牌提示：`请输入栖墨远程访问令牌`

### 保留的技术标识

为降低迁移风险，本轮不修改：

- API 请求头 `X-Novel-Agent-Token`
- localStorage 键 `novel-agent-access-token`
- Python 包名 `novel_agent`
- 后端进程名 `novel-agent-backend`
- Electron `appId` `com.novelagent.desktop`

这些标识不直接暴露为主品牌，可在未来单独安排兼容迁移。

## 山山边界

山山继续作为栖墨的默认内置助手：

- 保留山山名称、形象、桌面助手窗口和对话口吻。
- 保留山山相关头像、动画、托盘助手入口和配置项。
- 软件主图标不使用山山形象。
- 品牌文案不将山山描述为软件本体。

## 替换范围

优先修改当前完整构建入口 `web/frontend/`：

- `web/frontend/src/App.vue`
- `web/frontend/src/api.ts`
- `web/frontend/index.html`
- `web/frontend/package.json`
- `web/frontend/electron/main.ts`
- `web/frontend/electron/ipc/pet-ipc.ts`
- `web/frontend/electron/tray/tray-manager.ts`
- `web/frontend/electron/updater/auto-updater.ts`
- `web/frontend/public/favicon.svg`
- `web/frontend/build/icon.png`
- `web/frontend/build/icon.ico`

同步修改保留的 Electron 源码副本 `electron_version/` 中对应品牌入口，避免后续误用旧副本重新构建：

- `electron_version/package.json`
- `electron_version/electron/main.ts`
- `electron_version/electron/ipc/pet-ipc.ts`
- `electron_version/electron/tray/tray-manager.ts`
- `electron_version/electron/updater/auto-updater.ts`

生成产物目录中的旧品牌文本不手工修改，统一通过构建命令刷新。

## 旧品牌备份

旧名称、旧 favicon、旧桌面 PNG、旧桌面 ICO 和品牌相关源码已备份到：

`D:\design-assets\品牌候选方案\旧品牌备份`

## 验证标准

实施后需要满足：

1. 新 SVG 可被正常解析。
2. 新 PNG 与 ICO 均存在，桌面构建可以读取。
3. 前端构建通过。
4. Electron TypeScript 构建通过。
5. 源码品牌入口不再显示 `NovelAgent`，技术兼容标识除外。
6. 山山相关名称、素材和助手功能保持不变。

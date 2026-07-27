# Electron 目录约定

**Canonical 源码**：`web/frontend/electron/`

该目录是桌面主进程、preload、窗口和 IPC 的唯一源码。构建、测试与发布不得读取
`electron_version/` 或其他本地副本。

安全回归测试扫描 canonical TypeScript 源码，确保不使用 `execSync` 带 shell 字符串。
桌面图标位于 `web/frontend/build/`，是 Electron 打包输入并由 Git 跟踪。

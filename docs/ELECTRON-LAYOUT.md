# Electron 目录约定

**Canonical 源码**：`web/frontend/electron/`

历史副本 `electron_version/electron/` 仅用于旧打包流水线，新改动请只改 canonical 路径；发布前用 diff 或同步脚本对齐。

安全回归测试会扫描两处 `export.ts`，确保不使用 `execSync` 带 shell 字符串。
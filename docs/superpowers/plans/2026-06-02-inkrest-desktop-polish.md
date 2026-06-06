# 栖墨桌面端细节修订 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正栖墨桌面图标白边，并完成宠物面板、任务日志和侧栏品牌区的小范围视觉优化。

**Architecture:** 保持现有 Vue 与 Electron 结构不变。桌面图标在资源层修正透明通道；宠物气泡、任务日志和侧栏品牌区分别在现有组件内做局部调整；通过源码契约和构建验证防止回归。

**Tech Stack:** Vue 3, Pinia, Electron, Python Pillow, pytest, Vite

---

### Task 1: 增加界面修订契约测试

**Files:**
- Modify: `tests/test_brand_contract.py`
- Modify: `tests/test_workspace_ui_contract.py`

- [ ] 检查桌面图标角落透明度。
- [ ] 检查宠物状态按钮文案为 `中止`。
- [ ] 检查任务流水日志包含 `Refresh` 图标、`fetchTasks` 调用和刷新按钮。
- [ ] 检查侧栏品牌结构包含同行锁定与精简副标题。
- [ ] 运行定向测试并确认缺失能力导致失败。

### Task 2: 修正桌面图标透明通道

**Files:**
- Modify: `web/frontend/build/icon.png`
- Modify: `web/frontend/build/icon.ico`
- Modify: `electron_version/build/icon.png`
- Modify: `electron_version/build/icon.ico`

- [ ] 使用透明背景重新渲染 SVG。
- [ ] 生成包含常用 Windows 尺寸的 ICO。
- [ ] 同步桌面端副本资源。
- [ ] 运行品牌契约测试。

### Task 3: 调整三处 Vue 界面

**Files:**
- Modify: `web/frontend/src/views/PetBubbleView.vue`
- Modify: `web/frontend/src/components/TaskLog.vue`
- Modify: `web/frontend/src/App.vue`

- [ ] 将宠物状态卡中止按钮缩短为 `中止`。
- [ ] 为任务流水日志增加带 loading 状态的手动刷新按钮。
- [ ] 将侧栏品牌区改为同行中英文锁定结构，保留单行副标题。
- [ ] 运行界面契约测试。

### Task 4: 验证并重新封装

- [ ] 运行 `python -m pytest tests -q`。
- [ ] 运行 `npm run build`。
- [ ] 运行 `npm run build:electron`。
- [ ] 浏览器检查品牌区与日志刷新按钮。
- [ ] 运行 `npx electron-builder --win` 重新生成 Windows 产物。

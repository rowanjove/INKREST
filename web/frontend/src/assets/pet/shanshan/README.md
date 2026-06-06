# 山山桌宠资产

已按 `桌宠图片.md` 的第一阶段要求处理：

- `source/shanshan_original.png`：原图备份。
- `source/shanshan_transparent.png`：去棋盘格后的透明 PNG。
- `source/shanshan_master.png`：裁切后的透明母版。
- `static/idle_1024.png`、`idle_512.png`、`idle_256.png`、`idle_128.png`：桌宠静态尺寸。
- `expressions/`：MVP 状态占位图，当前基于同一静态图；后续建议重新生成/手绘 `working/success/error` 差分。
- `animations/`：基于静态图的轻微位移动画 WebP sheet 和 manifest。
- `ui/`：头像、气泡头像、托盘图标、通知图标和状态 badge。

注意：原图没有真实透明通道，自动去背景已经尽量保留白发和浅色衣服边缘，但头发细丝处仍建议人工检查。

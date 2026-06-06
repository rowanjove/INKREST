# Shanshan Chat Polish Design

## Goal

Make Shanshan's initial chat screen easier to scan while keeping the assistant useful and personable.

## Welcome Content

The initial message combines a light editorial-partner tone with a compact capability list:

```text
嗨，我是山山，栖墨里的驻场小编辑。

我可以帮你：
- 查任务进度和卡点
- 解释失败原因
- 告诉你该去哪个页面处理

你现在想先处理哪一件？
```

## Layout

The top capability boundary becomes a single muted line:

```text
查任务、解释失败、指路配置；批量续跑请到监控。
```

The first assistant message receives a dedicated `welcome` visual treatment: subtle tinted background, clearer spacing, and a light accent. Later assistant replies continue to use normal chat bubbles.

Suggested questions remain visible only before the first user message. They use compact wrapping chips:

- `这章为什么没过审？`
- `全书暂停了，怎么续跑？`
- `日常档和逻辑档怎么选？`

The input bar gets a clearer white surface, slightly larger padding, and a stronger focus state.

## Verification

UI contract tests assert the new content and welcome-card class. The frontend production build and full test suite must pass.


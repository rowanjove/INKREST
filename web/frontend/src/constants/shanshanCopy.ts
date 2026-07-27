/** 山山 UI 文案 — 与后端 persona 保持一致（文静 + 一点俏皮） */

export const SHANSHAN_WELCOME_CHAT = `嗨，我是山山，栖墨里的驻场小编辑。
我可以查任务进度、体量与已写章数，结合当前作品体量与门禁摘要排障，也能带你跳到正文、概览或生产中心。

你现在想先处理哪一件？`

export const SHANSHAN_CHAT_ERROR = (detail: string) =>
  `嗯，我这边暂时没连上：${detail}。稍后再试一次，或先去设置里看看模型配置。`

export const SHANSHAN_SUGGESTED_QUESTIONS = [
  '这章为什么没过审？',
  '全书暂停了，怎么续跑？',
  '日常档和逻辑档怎么选？',
  '当前作品还有哪些待处理？',
] as const

export const SHANSHAN_CHAT_PLACEHOLDER = '问山山：任务、配置、该打开哪一页…'

export const SHANSHAN_CONFIG_BLURB = '栖墨驻场小编辑，帮你盯稿、排障；对话可单独指定模型。'

/** 对话 Tab 顶部能力边界 */
export const SHANSHAN_CHAT_SCOPE =
  '结合当前作品体量与门禁摘要排障；待处理章节、续跑与任务日志统一在生产中心，单章改稿请到正文页。'

export const SHANSHAN_BATCH_PAUSE_HINT = (batch: {
  pause_reason?: string
  last_arc_id?: string
  last_chapter_id?: string
  fail_streak?: number
}) => {
  const reason = batch.pause_reason || 'circuit_breaker'
  const arc = batch.last_arc_id || '—'
  const ch = batch.last_chapter_id || '—'
  const streak =
    batch.fail_streak && batch.fail_streak > 0 ? `，连续失败 ${batch.fail_streak} 次` : ''
  return `全书批量已暂停（${reason}，卷 ${arc} / 章 ${ch}${streak}）。请到生产中心处理审校问题后再续跑。`
}

/** 针对待处理章的三步排障建议（对话 / 上下文注入） */
export const SHANSHAN_REPAIR_STEPS_HINT = (chapterId: string, stage?: string) => {
  const stageHint = stage ? `（当前：${stage}）` : ''
  return [
    `第 ${chapterId} 章${stageHint}建议顺序：`,
    '1. 去写作页改稿',
    '2. 到生产中心审校队列「重跑门禁」',
    '3. 通过后在生产中心确认「继续生产」',
  ].join('\n')
}

export const SHANSHAN_FIX_REPLY = {
  testModelOk: (latencyMs: number, preview: string) =>
    `模型连通正常，延迟约 ${latencyMs} ms。返回预览：「${preview}」`,
  retryTaskOk:
    '已提交本章重试。进度和门禁问题请到 **生产中心** 查看。',
  fixFailed: (reason: string) => `这一步没办成：${reason}`,
  fixError: (detail: string) => `执行时出了点状况：${detail}`,
} as const

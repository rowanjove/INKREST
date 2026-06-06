/** 复制章节正文到剪贴板（便于粘贴网文平台） */

export function formatChapterPlainText(ch: {
  chapter_id?: string
  title?: string
  final_text?: string
}): string {
  const title = (ch.title || '').trim()
  const body = (ch.final_text || '').trim()
  if (!body && !title) return ''
  if (title && body) {
    return `${title}\n\n${body}`
  }
  return body || title
}

export async function copyPlainTextToClipboard(text: string): Promise<void> {
  const value = text.trim()
  if (!value) {
    throw new Error('暂无正文可复制')
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value)
    return
  }
  const ta = document.createElement('textarea')
  ta.value = value
  ta.style.position = 'fixed'
  ta.style.left = '-9999px'
  document.body.appendChild(ta)
  ta.select()
  const ok = document.execCommand('copy')
  document.body.removeChild(ta)
  if (!ok) throw new Error('浏览器不支持复制')
}

export async function copyChapterPlainText(ch: {
  chapter_id?: string
  title?: string
  final_text?: string
}): Promise<number> {
  const text = formatChapterPlainText(ch)
  await copyPlainTextToClipboard(text)
  return text.length
}

export async function copyChapterTitleOnly(title?: string): Promise<number> {
  const text = (title || '').trim()
  if (!text) throw new Error('暂无标题可复制')
  await copyPlainTextToClipboard(text)
  return text.length
}

export async function copyChapterBodyOnly(final_text?: string): Promise<number> {
  const text = (final_text || '').trim()
  if (!text) throw new Error('暂无正文可复制')
  await copyPlainTextToClipboard(text)
  return text.length
}
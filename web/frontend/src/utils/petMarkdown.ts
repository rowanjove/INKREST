/** Lightweight Markdown renderer for pet chat bubbles (no external deps). */
export function renderPetMarkdown(text: string): string {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')
  html = html.replace(/`(.*?)`/g, '<code>$1</code>')
  html = html.replace(/\n/g, '<br>')
  html = html.replace(/(?:^|<br>)\s*-\s+(.*?)(?=$|<br>)/g, (_, p1) => {
    return `<div class="md-list-item"><span class="bullet">•</span> ${p1}</div>`
  })

  return html
}
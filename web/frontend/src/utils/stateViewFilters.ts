/** Pure filter/helpers for StateView settings & chronicle tabs */

export function matchesChapterRange(
  item: { chapter_id?: string | number } | null | undefined,
  range: [number, number],
): boolean {
  if (!item || !item.chapter_id) return true
  const num = parseInt(String(item.chapter_id))
  if (isNaN(num)) return true
  return num >= range[0] && num <= range[1]
}

export function maxChapterFromState(state: Record<string, any> | null | undefined): number {
  let maxVal = 1
  const check = (id: unknown) => {
    if (!id) return
    const num = parseInt(String(id))
    if (!isNaN(num) && num > maxVal) {
      maxVal = num
    }
  }
  if (state) {
    ;(state.foreshadows || []).forEach((x: { chapter_id?: unknown }) => check(x.chapter_id))
    ;(state.hooks || []).forEach((x: { chapter_id?: unknown }) => check(x.chapter_id))
    ;(state.events || []).forEach((x: { chapter_id?: unknown }) => check(x.chapter_id))
  }
  return maxVal
}

export function sliderMarksFromMax(maxChapter: number): Record<number, string> {
  const marks: Record<number, string> = {
    1: '第 1 章',
  }
  if (maxChapter > 1) {
    marks[maxChapter] = `第 ${maxChapter} 章`
  }
  return marks
}

export function mergeById(items: { id?: string | number }[]): any[] {
  const map = new Map<string, any>()
  for (const item of items) {
    if (!item?.id) continue
    map.set(String(item.id), { ...map.get(String(item.id)), ...item })
  }
  return Array.from(map.values())
}

export function emotionDotColor(emotion?: string): string {
  const e = emotion || ''
  return e.includes('怒') || e.includes('恨') ? 'var(--color-danger)' : 'var(--color-success)'
}
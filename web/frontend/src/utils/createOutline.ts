import { findScaleOption, isLongFormScale } from '../constants/scaleOptions'
import type { Composition } from '../types/preset'

export interface QuickCreatePayload {
  name: string
  description: string
  genre: string
  channel: string
  target_chapters: number
  scale: string
  scale_label: string
  target_chars_per_chapter: number[]
  composition: Composition | null
}

/** 快速创建落盘用最小大纲，与 AI/解析路径字段对齐 */
export function buildMinimalOutline(data: QuickCreatePayload): Record<string, unknown> {
  const opt = findScaleOption(data.scale)
  const target = data.target_chapters || opt?.target_chapters || 20
  const spanEnd = Math.min(target, opt?.scale === 'micro' ? 3 : 80)
  const genre =
    data.genre ||
    data.composition?.theme ||
    data.channel ||
    ''

  const scaleProfile: Record<string, unknown> = {
    scale: data.scale,
    label: data.scale_label,
    target_chapters: target,
    max_chapters: opt?.max_chapters ?? target,
    target_chars: data.target_chars_per_chapter,
  }

  return {
    title_options: [data.name],
    chosen_title: data.name.trim() || undefined,
    logline: data.description || data.name,
    core_theme: data.description || data.name,
    genre_positioning: genre,
    target_chapters: target,
    scale_profile: scaleProfile,
    reader_promise: data.description ? [data.description.slice(0, 120)] : ['精彩的故事'],
    protagonist: {
      name: '待定',
      desire: '待定',
      flaw: '待定',
      edge: '待定',
      limit: '待定',
    },
    main_cast: [],
    antagonistic_forces: ['待定'],
    forbidden_moves: [],
    macro_outline: [
      {
        arc_id: 'A01',
        name: '起始卷',
        chapters: `1-${Math.max(1, spanEnd)}`,
        goal: data.description || '确立主线与读者抓手',
        turning_point: '待定',
        payoff: '待定',
      },
    ],
  }
}

export interface PostCreateRoute {
  path: string
  preferOutline: boolean
}

export function resolvePostCreateRoute(scale: string, hasOutline: boolean): PostCreateRoute {
  const preferOutline = !hasOutline || isLongFormScale(scale)
  if (preferOutline) {
    return { path: '/outline', preferOutline: true }
  }
  return { path: '/workspace', preferOutline: false }
}
/** 作品体量档位 — 快速创建 / AI 引导 / 后端 scale_profile 共用 */

export type ScaleKey = 'micro' | 'short' | 'medium' | 'long' | 'epic' | 'infinite'

export interface ScaleOption {
  label: string
  scale: ScaleKey
  target_chapters: number
  hint: string
  max_chapters: number
  planning_mode?: string
  /** AI 引导用口语标签（与快速创建 label 可不同） */
  aiLabel?: string
}

export const SCALE_OPTIONS: ScaleOption[] = [
  { label: '微型短篇 (1-3章)', scale: 'micro', target_chapters: 1, hint: '单场景快速成稿', max_chapters: 3, planning_mode: 'single_shot' },
  { label: '短篇小说 (4-20章)', scale: 'short', target_chapters: 12, hint: '完整短篇', max_chapters: 20, planning_mode: 'full_upfront' },
  { label: '中篇小说 (20-100章)', scale: 'medium', target_chapters: 80, hint: '标准网文结构', max_chapters: 100, planning_mode: 'rolling_window' },
  { label: '长篇小说 (100-500章)', scale: 'long', target_chapters: 200, hint: '分卷滚动规划', max_chapters: 500, planning_mode: 'dynamic_volume' },
  { label: '超长篇巨著 (500-3000章)', scale: 'epic', target_chapters: 800, hint: '卷级骨架 + 滚动拆章', max_chapters: 3000, planning_mode: 'fractal_dynamic_volume' },
  { label: '无限更新连载', scale: 'infinite', target_chapters: 1200, hint: '单元化连载，按需续章', max_chapters: 999999, planning_mode: 'container_episode' },
]

export const SCALE_PLANNING_MODE_LABELS: Record<string, string> = {
  single_shot: '单章直出模式',
  full_upfront: '全局前置大纲模式',
  rolling_window: '滚动窗口自适应模式',
  dynamic_volume: '动态卷纲调整模式',
  fractal_dynamic_volume: '分形动态卷纲架构',
  container_episode: '单元化无限连载模式',
}

export function scalePlanningModeLabel(mode: string): string {
  return SCALE_PLANNING_MODE_LABELS[mode] || mode || '未设定'
}

export const AI_SCALE_OPTIONS: ScaleOption[] = SCALE_OPTIONS.map((o) => ({
  ...o,
  aiLabel:
    o.scale === 'micro'
      ? '一章以内'
      : o.scale === 'short'
        ? '几章'
        : o.scale === 'medium'
          ? '几十章'
          : o.scale === 'long'
            ? '一两百章'
            : o.scale === 'epic'
              ? '几百上千章'
              : '一直更新',
}))

export function findScaleOption(scale: string): ScaleOption | undefined {
  return SCALE_OPTIONS.find((o) => o.scale === scale)
}

export function targetChaptersInputMax(scale: string): number {
  if (scale === 'infinite') return 999999
  const opt = findScaleOption(scale)
  return opt?.max_chapters ?? 3000
}

export function isLongFormScale(scale: string): boolean {
  return scale === 'long' || scale === 'epic' || scale === 'infinite'
}

export function longFormScaleHint(scale: string): string | null {
  if (scale === 'epic') {
    return '超长篇：此处只定体量与卷级骨架；细章由主编按规划窗口滚动生成，请在大纲页确认卷纲后于工作台分批开跑。'
  }
  if (scale === 'infinite') {
    return '无限连载：按「集」滚动规划章节，不写完全书细纲；工作台支持分批续跑。'
  }
  if (scale === 'long') {
    return '长篇：建议在大纲页生成卷纲后，用工作台「连写启动」按本轮章数续跑。'
  }
  return null
}
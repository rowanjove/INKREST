import type { ProjectSnapshot } from '../project/projectSnapshot'

export type PublishingTab = 'preview' | 'platform' | 'export'
export type ExportFormat = 'txt' | 'markdown' | 'docx' | 'epub' | 'pdf'

export interface PublicationBookSummary {
  title: string
  author: string
  language: string
  chapter_count: number
  word_count: number
}

export interface PublicationChapterSummary {
  chapter_id: string
  title: string
  revision: number
  word_count: number
  has_content: boolean
  updated_at: string
}

export interface PublicationChapter {
  chapter_id: string
  title: string
  plain_text: string
  markdown_text: string
  revision: number
  word_count: number
}

export interface PreflightItem {
  code: string
  severity: 'blocking' | 'warning' | 'ready'
  label: string
  detail: string
  route: string
}

export interface ExportPreflight {
  can_export: boolean
  blocking_count: number
  warning_count: number
  items: PreflightItem[]
}

export interface PublicationFormat {
  id: ExportFormat
  label: string
  available: boolean
  extension: string
}

export interface PublicationPlatform {
  id: string
  label: string
  pacing_density: number
  setting_detail_weight: number
  dialogue_ratio_range: [number, number]
  style_summary: string
  golden_three_rules: string
  avoid: string[]
}

export interface PublishingWorkspace {
  schema_version: 1
  snapshot: ProjectSnapshot
  book: PublicationBookSummary
  chapters: PublicationChapterSummary[]
  selected_chapter_id: string
  selected_chapter: PublicationChapter | null
  platform: PublicationPlatform
  platform_check: {
    status: string
    items: Array<{
      code: string
      status: 'ready' | 'pending' | 'review'
      label: string
      detail: string
    }>
  }
  golden_check: {
    status: 'ready' | 'incomplete'
    ready_count: number
    required_count: number
    checks: Array<{
      chapter_id: string
      label: string
      status: 'ready' | 'missing'
      word_count: number
    }>
  }
  feedback: Array<{
    id: number
    chapter_id: string
    bounce_rate: number
    retention_rate: number
    active_readers: number
    updated_at: string
  }>
  preflight: ExportPreflight
  formats: PublicationFormat[]
}

export interface ReaderSettings {
  fontSize: number
  lineHeight: number
  width: number
  indent: boolean
}

export function preflightTone(
  severity: PreflightItem['severity'],
): 'danger' | 'warning' | 'success' {
  if (severity === 'blocking') return 'danger'
  if (severity === 'warning') return 'warning'
  return 'success'
}

export function formatWordCount(value: number): string {
  if (value >= 10_000) return `${(value / 10_000).toFixed(value >= 100_000 ? 0 : 1)} 万`
  return value.toLocaleString('zh-CN')
}

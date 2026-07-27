import type { JSONContent } from '@tiptap/core'

export type ManuscriptChapterStatus = 'draft' | 'ready' | 'attention'
export type ManuscriptSaveStatus =
  | 'idle'
  | 'dirty'
  | 'saving'
  | 'saved'
  | 'error'
  | 'conflict'
export type ManuscriptRevisionSource = 'import' | 'autosave' | 'manual' | 'ai_accept' | 'restore'
export type AiEditKind = 'rewrite' | 'polish' | 'shorten' | 'expand' | 'continue'

export interface ManuscriptChapter {
  chapter_id: string
  title: string
  word_count: number
  status: ManuscriptChapterStatus
  status_label: string
  has_content: boolean
}

export interface ManuscriptDocument {
  document_id: string
  chapter_id: string
  title: string
  content_json: JSONContent
  plain_text: string
  markdown_text: string
  revision: number
  source: ManuscriptRevisionSource
  created_at: string
  updated_at: string
}

export interface ManuscriptRevision {
  revision_id: string
  document_id: string
  chapter_id: string
  revision: number
  title: string
  content_json: JSONContent
  plain_text: string
  markdown_text: string
  source: ManuscriptRevisionSource
  created_at: string
}

export interface ManuscriptContext {
  chapter_goal?: string
  synopsis?: string
  target_chars?: number[]
  risk_level?: string
  gate_status?: string
}

export interface ManuscriptWorkspace {
  schema_version: number
  chapters: ManuscriptChapter[]
  selected_chapter_id: string
  document: ManuscriptDocument | null
  history: ManuscriptRevision[]
  context: ManuscriptContext
}

export interface EditorSelection {
  text: string
  from: number
  to: number
  x: number
  y: number
}

export interface AiEditIntent {
  kind: AiEditKind
  label: string
  instruction: string
  chapterId: string
  selection: EditorSelection
}

export interface AiEditSuggestion extends AiEditIntent {
  replacement: string
}

export const EMPTY_TIPTAP_DOCUMENT: JSONContent = {
  type: 'doc',
  content: [{ type: 'paragraph' }],
}

export const SAVE_STATUS_LABELS: Record<ManuscriptSaveStatus, string> = {
  idle: '等待编辑',
  dirty: '有未保存修改',
  saving: '正在保存…',
  saved: '已自动保存',
  error: '保存失败',
  conflict: '发现版本冲突',
}

export const REVISION_SOURCE_LABELS: Record<ManuscriptRevisionSource, string> = {
  import: '从旧稿导入',
  autosave: '自动保存',
  manual: '手动节点',
  ai_accept: '采纳 AI 建议',
  restore: '恢复历史',
}

const AI_INTENT_META: Record<AiEditKind, { label: string; instruction: string }> = {
  rewrite: { label: '改写', instruction: '保持原意，重写这段文字，使表达更自然。' },
  polish: { label: '润色', instruction: '润色这段文字，增强节奏、画面感和语言质感。' },
  shorten: { label: '精简', instruction: '精简这段文字，删除重复信息，保留关键情节。' },
  expand: { label: '扩写', instruction: '扩写这段文字，补充合理的动作、感官或心理细节。' },
  continue: { label: '续写', instruction: '承接光标前的正文继续写作。' },
}

export function createAiEditIntent(
  kind: AiEditKind,
  chapterId: string,
  selection: EditorSelection,
): AiEditIntent {
  const meta = AI_INTENT_META[kind]
  return {
    kind,
    label: meta.label,
    instruction: meta.instruction,
    chapterId,
    selection,
  }
}

export function saveStatusTone(
  status: ManuscriptSaveStatus,
): 'neutral' | 'info' | 'success' | 'warning' | 'danger' {
  if (status === 'saved') return 'success'
  if (status === 'saving') return 'info'
  if (status === 'dirty' || status === 'conflict') return 'warning'
  if (status === 'error') return 'danger'
  return 'neutral'
}

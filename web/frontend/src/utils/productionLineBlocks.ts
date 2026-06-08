import { PRODUCTION_BLOCKS } from '../constants/pipelineDisplay'
import type { ProgressEntry } from '../stores/tasks'

export type BlockStatus = 'idle' | 'running' | 'done' | 'error' | 'paused'

export const QUEUE_PIPELINE_STEPS = new Set([
  'ensure_queue',
  'managing_editor',
  'novel_batch',
  'novel_autopilot',
])

export function blockIndexForStep(step: string): number {
  return PRODUCTION_BLOCKS.findIndex((block) => block.steps.includes(step))
}

export function rawBlockStatus(
  steps: string[],
  entries: ProgressEntry[],
): BlockStatus {
  const relevant = entries.filter((e) => steps.includes(e.step))
  if (!relevant.length) return 'idle'
  if (relevant.some((e) => e.status === 'running')) return 'running'
  if (relevant.some((e) => e.status === 'error' || e.status === 'blocked')) return 'error'
  if (relevant.some((e) => e.status === 'warning')) return 'error'
  const touched = relevant.filter((e) => e.status !== 'skipped')
  if (
    touched.length > 0 &&
    touched.every((e) => e.status === 'done' || e.status === 'skipped')
  ) {
    return 'done'
  }
  if (relevant.some((e) => e.status === 'done')) return 'running'
  return 'idle'
}

export function chapterPipelineTouched(
  entries: ProgressEntry[],
  chapterId: string,
): boolean {
  if (!chapterId) return false
  return entries.some(
    (e) =>
      e.chapter_id === chapterId &&
      !QUEUE_PIPELINE_STEPS.has(e.step) &&
      (e.status === 'running' || e.status === 'done'),
  )
}

export type ProductionBlockView = {
  id: string
  index: number
  status: BlockStatus
  detailLabel: string
  chapterId: string
  label: string
  desc: string
  steps: string[]
}

export function applyRunningPipelineOverlay(
  blocks: ProductionBlockView[],
  options: {
    pipelineBusy: boolean
    entries: ProgressEntry[]
  },
): ProductionBlockView[] {
  const { pipelineBusy, entries } = options
  if (!pipelineBusy) return blocks

  let runIdx = blocks.findIndex((b) => b.status === 'running')
  if (runIdx < 0) {
    const runningEntry = [...entries].reverse().find((e) => e.status === 'running')
    if (runningEntry) {
      runIdx = blockIndexForStep(runningEntry.step)
    }
  }
  if (runIdx < 0) {
    runIdx = blocks.findIndex((b) => b.status === 'idle' || b.status === 'paused')
  }
  if (runIdx < 0) return blocks

  return blocks.map((block, index) => {
    if (block.status === 'error' || block.status === 'paused' || block.status === 'done') {
      return block
    }
    if (index < runIdx) {
      return { ...block, status: 'done' as BlockStatus, detailLabel: '', chapterId: '' }
    }
    if (index === runIdx) {
      return { ...block, status: 'running' as BlockStatus }
    }
    return block
  })
}

export function settleQueueBlockAfterChapterStart(
  blocks: ProductionBlockView[],
  entries: ProgressEntry[],
  activeChapterId: string,
): ProductionBlockView[] {
  if (!chapterPipelineTouched(entries, activeChapterId)) return blocks
  return blocks.map((block) => {
    if (block.id !== 'queue' || block.status === 'error') return block
    return { ...block, status: 'done' as BlockStatus, detailLabel: '', chapterId: '' }
  })
}
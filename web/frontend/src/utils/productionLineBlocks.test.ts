import { describe, expect, it } from 'vitest'
import {
  applyRunningPipelineOverlay,
  chapterPipelineTouched,
  rawBlockStatus,
  settleQueueBlockAfterChapterStart,
} from './productionLineBlocks'
import type { ProgressEntry } from '../stores/tasks'

describe('productionLineBlocks', () => {
  it('marks queue block done once chapter pipeline has started', () => {
    const entries: ProgressEntry[] = [
      { step: 'ensure_queue', status: 'running', chapter_id: '', timestamp: 1 },
      { step: 'writer', status: 'running', chapter_id: '002', timestamp: 2 },
    ]
    expect(chapterPipelineTouched(entries, '002')).toBe(true)
    const blocks = settleQueueBlockAfterChapterStart(
      [
        {
          id: 'queue',
          index: 0,
          status: 'running',
          detailLabel: '同步卷队列',
          chapterId: '',
          label: '卷队列',
          desc: '',
          steps: ['ensure_queue'],
        },
        {
          id: 'write',
          index: 2,
          status: 'running',
          detailLabel: '写作引擎',
          chapterId: '002',
          label: '写手',
          desc: '',
          steps: ['writer'],
        },
      ],
      entries,
      '002',
    )
    expect(blocks[0]?.status).toBe('done')
    expect(blocks[1]?.status).toBe('running')
  })

  it('keeps later done blocks when overlaying running pipeline', () => {
    const blocks = [
      { id: 'queue', index: 0, status: 'done' as const, detailLabel: '', chapterId: '', label: '卷队列', desc: '', steps: ['ensure_queue'] },
      { id: 'plan', index: 1, status: 'done' as const, detailLabel: '', chapterId: '', label: '大纲编剧', desc: '', steps: ['planner'] },
      { id: 'write', index: 2, status: 'idle' as const, detailLabel: '', chapterId: '', label: '写手', desc: '', steps: ['writer'] },
      { id: 'polish', index: 3, status: 'idle' as const, detailLabel: '', chapterId: '', label: '润色', desc: '', steps: ['style_editor'] },
      { id: 'audit', index: 4, status: 'idle' as const, detailLabel: '', chapterId: '', label: '审校', desc: '', steps: ['auditor'] },
      { id: 'gate', index: 5, status: 'idle' as const, detailLabel: '', chapterId: '', label: 'QA', desc: '', steps: ['unified_gate'] },
    ]
    const entries: ProgressEntry[] = [
      { step: 'writer', status: 'running', chapter_id: '002', timestamp: 1 },
    ]
    const overlaid = applyRunningPipelineOverlay(blocks, {
      pipelineBusy: true,
      entries,
    })
    expect(overlaid[0]?.status).toBe('done')
    expect(overlaid[1]?.status).toBe('done')
    expect(overlaid[2]?.status).toBe('running')
    expect(overlaid[3]?.status).toBe('idle')
  })

  it('detects done queue sync', () => {
    const entries: ProgressEntry[] = [
      { step: 'ensure_queue', status: 'done', chapter_id: '', timestamp: 1 },
    ]
    expect(rawBlockStatus(['ensure_queue', 'managing_editor'], entries)).toBe('done')
  })
})
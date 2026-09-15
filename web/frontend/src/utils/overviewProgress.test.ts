import { describe, expect, it } from 'vitest'

import { progressHasSourceMismatch, progressTone, queueTone } from './overviewProgress'

describe('overview progress helpers', () => {
  it('treats the batch counter as authoritative while flagging source drift', () => {
    const progress = {
      authoritative_completed: 12,
      library_indexed: 12,
      disk_chapters_with_final: 10,
      pending_total: 0,
      pending_gate_count: 0,
      batch_paused: false,
    }

    expect(progressHasSourceMismatch(progress)).toBe(true)
    expect(progressTone(progress)).toBe('warning')
  })

  it('prioritises pending gates and paused batches in the summary tone', () => {
    expect(progressTone({ authoritative_completed: 1, pending_gate_count: 1 })).toBe('danger')
    expect(progressTone({ authoritative_completed: 1, pending_total: 2 })).toBe('warning')
  })

  it('marks a stale or incomplete outline queue as needing attention', () => {
    expect(queueTone({ arc_queue_stale: { stale: true } })).toBe('warning')
    expect(queueTone({ pending_briefs: 0, target_chapters: 20, last_written_chapter: 4 })).toBe('warning')
    expect(queueTone({ pending_briefs: 3 })).toBe('success')
  })
})

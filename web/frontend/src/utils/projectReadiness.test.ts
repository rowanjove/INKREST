import { describe, expect, it } from 'vitest'
import {
  buildReadinessItems,
  longFormVectorWarn,
  mergeServerReadinessPending,
  readinessCanContinue,
  resolveVectorContextFromApis,
} from './projectReadiness'

const baseOutline = {
  macro_outline: [{ arc_id: 'A1' }],
  chosen_title: '测试书',
  scale_profile: { scale: 'long', max_chapters: 200 },
  target_chapters: 200,
}

const baseAssets = [
  { name: 'world_bible', size: 10 },
  { name: 'style_guide', size: 10 },
  { name: 'rules', size: 10 },
  { name: 'sensitive_words', size: 10 },
]

describe('resolveVectorContextFromApis', () => {
  it('forces semantic off when vector_blocks_continue', () => {
    const ctx = resolveVectorContextFromApis(
      { vector_blocks_continue: true },
      { semantic_search_effective: true, vector_enabled: true },
    )
    expect(ctx.semanticSearchEffective).toBe(false)
    expect(ctx.vectorBlocksContinue).toBe(true)
  })
})

describe('buildReadinessItems', () => {
  it('blocks embedding row when vector_blocks_continue', () => {
    const items = buildReadinessItems({
      engineReady: true,
      outline: baseOutline,
      assets: baseAssets,
      maxAvailableChapters: 5,
      semanticSearchEffective: false,
      vectorEnabled: true,
      vectorBlocksContinue: true,
      workScale: 'long',
    })
    const embedding = items.find((item) => item.id === 'embedding')
    expect(embedding?.ok).toBe(false)
    expect(readinessCanContinue({ items, serverOk: true })).toBe(false)
  })
})

describe('mergeServerReadinessPending', () => {
  it('maps server vector pending onto embedding row', () => {
    const base = buildReadinessItems({
      engineReady: true,
      outline: baseOutline,
      assets: baseAssets,
      maxAvailableChapters: 5,
      workScale: 'long',
    })
    const merged = mergeServerReadinessPending(base, [
      { id: 'vector', label: '长篇模式需配置有效 Embedding（非 stub）' },
    ])
    expect(merged.find((item) => item.id === 'embedding')?.ok).toBe(false)
  })
})

describe('longFormVectorWarn', () => {
  it('warns on long scale when semantic search ineffective', () => {
    expect(
      longFormVectorWarn({
        workScale: 'long',
        vectorEnabled: true,
        semanticSearchEffective: false,
      }),
    ).toBe(true)
  })

  it('respects vectorReadinessLevel ignore', () => {
    expect(
      longFormVectorWarn({
        workScale: 'epic',
        vectorEnabled: true,
        semanticSearchEffective: false,
        vectorReadinessLevel: 'ignore',
      }),
    ).toBe(false)
  })
})
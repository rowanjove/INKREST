import { describe, expect, it } from 'vitest'
import {
  longFormVectorWarn,
  resolveVectorContextFromApis,
} from './projectReadiness'

describe('resolveVectorContextFromApis', () => {
  it('forces semantic off when vector_blocks_continue', () => {
    const ctx = resolveVectorContextFromApis(
      { vector_blocks_continue: true },
      { semantic_search_effective: true, vector_enabled: true },
    )
    expect(ctx.semanticSearchEffective).toBe(false)
    expect(ctx.vectorEnabled).toBe(true)
  })

  it('merges readiness embedding fields', () => {
    const ctx = resolveVectorContextFromApis(
      {
        embedding_backend: 'chromadb',
        chromadb_available: false,
        embedding_backend_hint: 'install chromadb',
        vector_readiness_level: 'warn',
      },
      { semantic_search_effective: true },
    )
    expect(ctx.embeddingBackend).toBe('chromadb')
    expect(ctx.chromadbAvailable).toBe(false)
    expect(ctx.embeddingBackendHint).toBe('install chromadb')
    expect(ctx.vectorReadinessLevel).toBe('warn')
    expect(ctx.semanticSearchEffective).toBe(true)
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
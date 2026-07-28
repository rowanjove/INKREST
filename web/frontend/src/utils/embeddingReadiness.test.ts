import { describe, expect, it } from 'vitest'
import { deriveEmbeddingReadiness } from './embeddingReadiness'

describe('deriveEmbeddingReadiness', () => {
  it('summarizes enabled cloud providers that are semantically ready', () => {
    const readiness = deriveEmbeddingReadiness({
      has_onnx: false,
      has_transformers: false,
      has_model: false,
      provider: 'bailian',
      vector_enabled: true,
      semantic_search_effective: true,
    })

    expect(readiness.providerLabel).toBe('云端 · 阿里百炼')
    expect(readiness.statusTone).toBe('ok')
    expect(readiness.statusLabel).toBe('就绪')
    expect(readiness.semanticLabel).toBe('生效中')
    expect(readiness.vectorDegraded).toBe(false)
    expect(readiness.alert).toBeNull()
  })

  it('reports degraded long-form vector setup with a concrete fix hint', () => {
    const readiness = deriveEmbeddingReadiness({
      has_onnx: true,
      has_transformers: true,
      has_model: false,
      provider: 'stub',
      vector_enabled: true,
      semantic_search_effective: false,
      long_form_vector_recommended: true,
    })

    expect(readiness.providerLabel).toBe('Stub（关键词）')
    expect(readiness.statusTone).toBe('warn')
    expect(readiness.statusLabel).toBe('待配置')
    expect(readiness.dependencyLabel).toBe('未部署')
    expect(readiness.alert).toEqual({
      type: 'warning',
      title: '语义检索未生效',
      message:
        '长篇/超长篇已开启向量能力，但当前为 Stub 或未配置密钥。重复剧情检测与语义召回不会真正执行，请选择下方方案之一。',
    })
    expect(readiness.fixSteps).toContain('配置云端 API Key 或部署本地 BGE')
  })

  it('keeps short-form disabled vector state muted instead of warning', () => {
    const readiness = deriveEmbeddingReadiness({
      has_onnx: true,
      has_transformers: true,
      has_model: true,
      provider: 'local',
      vector_enabled: false,
      semantic_search_effective: false,
    })

    expect(readiness.statusTone).toBe('muted')
    expect(readiness.statusLabel).toBe('已关闭')
    expect(readiness.semanticLabel).toBe('体量已关闭')
    expect(readiness.depsReady).toBe(true)
    expect(readiness.dependencyLabel).toBe('环境 + 模型就绪')
    expect(readiness.alert?.type).toBe('info')
  })
})

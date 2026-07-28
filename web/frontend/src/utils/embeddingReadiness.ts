export type EmbeddingStatusTone = 'ok' | 'warn' | 'muted'

export interface EmbeddingStatusInput {
  has_onnx: boolean
  has_transformers: boolean
  has_model: boolean
  provider: string
  vector_enabled?: boolean
  semantic_search_effective?: boolean
  long_form_vector_recommended?: boolean
}

export interface EmbeddingReadinessAlert {
  type: 'warning' | 'info'
  title: string
  message: string
}

export interface EmbeddingReadiness {
  providerLabel: string
  semanticOk: boolean
  vectorOn: boolean
  vectorDegraded: boolean
  depsReady: boolean
  statusTone: EmbeddingStatusTone
  statusLabel: string
  semanticLabel: string
  dependencyLabel: string
  alert: EmbeddingReadinessAlert | null
  fixSteps: string[]
}

export function providerDisplayName(provider: string): string {
  if (provider === 'local') return '本地 BGE-Micro'
  if (provider === 'stub') return 'Stub（关键词）'
  if (provider === 'zhipu') return '云端 · 智谱'
  if (provider === 'dashscope' || provider === 'bailian') return '云端 · 阿里百炼'
  if (provider === 'openai') return '云端 · OpenAI 兼容'
  return provider
}

export function deriveEmbeddingReadiness(status: EmbeddingStatusInput): EmbeddingReadiness {
  const semanticOk = Boolean(status.semantic_search_effective)
  const vectorOn = status.vector_enabled !== false
  const vectorDegraded = vectorOn && !semanticOk
  const depsReady = status.has_onnx && status.has_transformers && status.has_model
  const statusTone: EmbeddingStatusTone = !vectorOn ? 'muted' : semanticOk ? 'ok' : 'warn'

  const alert = vectorDegraded
    ? {
        type: 'warning' as const,
        title: '语义检索未生效',
        message:
          '长篇/超长篇已开启向量能力，但当前为 Stub 或未配置密钥。重复剧情检测与语义召回不会真正执行，请选择下方方案之一。',
      }
    : !vectorOn
      ? {
          type: 'info' as const,
          title: '短篇体量无需向量',
          message: '微型/短篇档位默认关闭向量索引；在工作台升级体量后会自动要求配置嵌入。',
        }
      : null

  const fixSteps = vectorDegraded
    ? [
        '配置云端 API Key 或部署本地 BGE',
        status.has_model ? '切换到本地 BGE 并重建索引' : '下载本地 BGE 模型后重建索引',
      ]
    : []

  return {
    providerLabel: providerDisplayName(status.provider),
    semanticOk,
    vectorOn,
    vectorDegraded,
    depsReady,
    statusTone,
    statusLabel: statusTone === 'ok' ? '就绪' : statusTone === 'warn' ? '待配置' : '已关闭',
    semanticLabel: !vectorOn ? '体量已关闭' : semanticOk ? '生效中' : '未生效',
    dependencyLabel: depsReady ? '环境 + 模型就绪' : status.has_model ? '模型已下载' : '未部署',
    alert,
    fixSteps,
  }
}

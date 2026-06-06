export interface EmbeddingCloudPreset {
  id: string
  name: string
  provider: 'zhipu' | 'openai' | 'dashscope'
  base_url: string
  model: string
  description: string
}

/** 云端向量嵌入一键预置（OpenAI 兼容 /embeddings 接口） */
export const EMBEDDING_CLOUD_PRESETS: EmbeddingCloudPreset[] = [
  {
    id: 'zhipu',
    name: '智谱 AI',
    provider: 'zhipu',
    base_url: 'https://open.bigmodel.cn/api/paas/v4',
    model: 'text-embedding-3',
    description: '智谱 text-embedding-3，中文语义检索表现稳定。',
  },
  {
    id: 'dashscope',
    name: '阿里百炼',
    provider: 'dashscope',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'text-embedding-v3',
    description: '百炼 DashScope 兼容模式，推荐 text-embedding-v3。',
  },
  {
    id: 'openai',
    name: 'OpenAI 兼容',
    provider: 'openai',
    base_url: 'https://api.openai.com/v1',
    model: 'text-embedding-3-small',
    description: 'OpenAI 官方或任意兼容网关。',
  },
]

export function resolveEmbeddingCloudEndpoint(provider: string, baseUrl: string, model: string) {
  if (provider === 'zhipu') {
    return {
      base_url: 'https://open.bigmodel.cn/api/paas/v4',
      model: 'text-embedding-3',
    }
  }
  if (provider === 'dashscope') {
    return {
      base_url: baseUrl?.trim() || 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      model: model?.trim() || 'text-embedding-v3',
    }
  }
  return {
    base_url: baseUrl?.trim() || 'https://api.openai.com/v1',
    model: model?.trim() || 'text-embedding-3-small',
  }
}
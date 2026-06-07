export type ConfigSection = { id: string; label: string }

export const CONFIG_SECTIONS: ConfigSection[] = [
  { id: 'appearance', label: '外观' },
  { id: 'models', label: '模型库' },
  { id: 'embedding-config', label: '向量嵌入' },
  { id: 'pipeline-runtime', label: '流水线' },
  { id: 'llm-routing', label: 'Agent 路由' },
  { id: 'writing-rules', label: '写作规范' },
  { id: 'agent-bridge', label: 'Agent 接入' },
]
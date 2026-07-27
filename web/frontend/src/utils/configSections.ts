export type ConfigSection = { id: string; label: string }

export const CONFIG_SECTIONS: ConfigSection[] = [
  { id: 'models-providers', label: '模型与提供方' },
  { id: 'memory', label: '记忆' },
  { id: 'generation-quality', label: '生成与质量' },
  { id: 'writing-layout', label: '写作与排版' },
  { id: 'extensions', label: '扩展' },
  { id: 'system-data', label: '系统与数据' },
]

export const CONFIG_SECTION_ALIASES: Record<string, string> = {
  appearance: 'system-data',
  models: 'models-providers',
  'embedding-config': 'memory',
  'pipeline-runtime': 'generation-quality',
  'llm-routing': 'models-providers',
  'writing-rules': 'writing-layout',
  'agent-bridge': 'extensions',
}

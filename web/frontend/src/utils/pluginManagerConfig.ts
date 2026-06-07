export interface PluginInfo {
  name: string
  display_name: string
  version: string
  description: string
  author: string
  icon: string
  plugin_type: string
  requires: string[]
  min_core_version: string
  enabled: boolean
  trusted?: boolean
  loaded?: boolean
  installed_version?: string
  config_schema: any
  config: Record<string, any>
  source: string
}

export const pluginTypes = [
  { value: 'pipeline_hook', label: '流水线钩子 (Pipeline Hook)' },
  { value: 'quality_guard', label: '质量检查 (Quality Guard)' },
  { value: 'exporter', label: '文件导出器 (Exporter)' },
  { value: 'llm_provider', label: 'LLM 提供商 (LLM Provider)' },
  { value: 'agent_override', label: 'Agent 替换 (Agent Override)' },
  { value: 'pipeline_phase', label: '流水线阶段 (Pipeline Phase)' },
  { value: 'vector_store', label: '向量数据库 (Vector Store)' },
  { value: 'embedding_provider', label: '文本嵌入 (Embedding)' },
  { value: 'approval_strategy', label: '审批策略 (Approval)' },
  { value: 'rules_extension', label: '规则扩展 (Rules)' },
  { value: 'prompt_enhancer', label: 'Prompt 增强 (Enhancer)' },
  { value: 'event_listener', label: '事件监听 (Listener)' },
  { value: 'web_extension', label: 'Web 页面 (Web Ext)' },
  { value: 'sensitive_scanner', label: '敏感词扫描 (Scanner)' },
  { value: 'command', label: '命令行工具 (Command)' },
] as const

export function getTypeLabel(typeVal: string): string {
  return pluginTypes.find((t) => t.value === typeVal)?.label || typeVal
}

export function hasSchemaForm(plugin: PluginInfo): boolean {
  return !!(plugin.config_schema?.properties && Object.keys(plugin.config_schema.properties).length > 0)
}
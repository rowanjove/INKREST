import { Brush, Collection, List, User, Warning } from '@element-plus/icons-vue'
import type { Component } from 'vue'

export type AssetItem = {
  name: string
  label?: string
  path: string
  exists: boolean
  size: number
  custom?: boolean
}

export type AssetTypeKey = 'character_cards' | 'world_bible' | 'style_guide' | 'rules' | 'custom'

export type AssetTypeOption = {
  key: AssetTypeKey
  label: string
  defaultName: string
  defaultLabel: string
  defaultAttributes: string[]
  defaultParameters: Record<string, string>
  helper: string
}

export type AssetMeta = {
  group: string
  icon: Component
  tone: string
  description: string
}

export const assetNames: Record<string, string> = {
  character_cards: '角色卡',
  world_bible: '世界观',
  terminology: '名词解释',
  style_guide: '风格指南',
  rules: '写作规则',
  sensitive_words: '敏感词过滤',
}

export const assetMeta: Record<string, AssetMeta> = {
  character_cards: { group: '人物资产', icon: User, tone: 'blue', description: '主角、配角、反派、关系网与出场状态。' },
  world_bible: { group: '设定资产', icon: Collection, tone: 'green', description: '世界规则、地点、势力、资源和禁忌。' },
  terminology: { group: '设定资产', icon: Collection, tone: 'green', description: '专有名词解释、专业术语与特殊名词说明。' },
  style_guide: { group: '写作资产', icon: Brush, tone: 'purple', description: '文风、节奏、对白、镜头和禁用表达。' },
  rules: { group: '写作资产', icon: List, tone: 'orange', description: '章节结构、质量检查、输出格式和流程约束。' },
  sensitive_words: { group: '写作资产', icon: Warning, tone: 'red', description: '与设置→写作规范→敏感词库同一文件；建议主要在设置页编辑。' },
}

export const assetTypeOptions: AssetTypeOption[] = [
  {
    key: 'character_cards',
    label: '角色卡',
    defaultName: 'character_cards',
    defaultLabel: '角色卡',
    defaultAttributes: ['姓名', '定位', '欲望', '秘密', '关系', '出场状态'],
    defaultParameters: { 角色层级: '主角/配角/反派', 关系密度: '高', 冲突方向: '与主线绑定' },
    helper: '适合批量生成主角、配角、反派、组织成员等可复用人物卡。',
  },
  {
    key: 'world_bible',
    label: '世界观',
    defaultName: 'world_bible',
    defaultLabel: '世界观',
    defaultAttributes: ['时代背景', '地理格局', '势力结构', '资源规则', '禁忌', '主线矛盾'],
    defaultParameters: { 世界类型: '都市/玄幻/科幻/历史', 规则硬度: '中', 可扩展性: '长期连载' },
    helper: '适合生成世界规则、地域、势力、技术/能力体系和长期矛盾。',
  },
  {
    key: 'style_guide',
    label: '风格指南',
    defaultName: 'style_guide',
    defaultLabel: '风格指南',
    defaultAttributes: ['叙事人称', '句式节奏', '情绪基调', '对白风格', '描写比例', '禁用表达'],
    defaultParameters: { 文风目标: '网文爽感', 节奏: '快', 读者体感: '清晰有钩子' },
    helper: '适合约束文风、节奏、对白、镜头感和 AI 腔规避策略。',
  },
  {
    key: 'rules',
    label: '写作规则',
    defaultName: 'rules',
    defaultLabel: '写作规则',
    defaultAttributes: ['章节结构', '冲突推进', '伏笔回收', '禁忌事项', '质量检查', '输出格式'],
    defaultParameters: { 平台: '通用', 单章目标: '2000-3000字', 审核强度: '中' },
    helper: '适合生成可被 Agent 读取的规则、检查项、流程约束，优先保存为 YAML。',
  },
  {
    key: 'custom',
    label: '自定义素材',
    defaultName: 'generated_asset',
    defaultLabel: '自定义素材',
    defaultAttributes: ['名称', '用途', '关键设定', '使用场景'],
    defaultParameters: { 输出格式: 'Markdown', 复用方式: '供章节生成参考' },
    helper: '适合地点、组织、道具、案件、职业体系等项目专属素材。',
  },
]

export const formatAssetSize = (size: number) => {
  if (!size) return '未创建'
  if (size < 1024) return `${size} B`
  return `${(size / 1024).toFixed(1)} KB`
}
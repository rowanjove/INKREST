import type { SnapshotAction } from '../../entities/project/projectSnapshot'
import type { PluginNavigationContribution } from '../../entities/plugin/pluginNavigation'
import { GLOBAL_NAV_ITEMS, PROJECT_NAV_ITEMS } from '../router/navigation'
import { resolveSnapshotActionHref } from '../shell/workflowActions'

export type CommandGroup = '全局' | '项目' | '设置' | '章节' | '人物' | '下一步'

export interface AppCommand {
  id: string
  label: string
  description: string
  group: CommandGroup
  path: string
  keywords: readonly string[]
  executeMode: 'navigate'
  disabled?: boolean
}

const SETTINGS_COMMANDS: readonly AppCommand[] = [
  {
    id: 'settings-models',
    label: '模型与提供方',
    description: '配置日常、推理和备用模型',
    group: '设置',
    path: '/config#models-providers',
    keywords: ['模型', 'provider', 'api key', 'llm', 'model-library'],
    executeMode: 'navigate',
  },
  {
    id: 'settings-embedding',
    label: 'Embedding 与记忆',
    description: '配置语义检索和向量索引',
    group: '设置',
    path: '/config#memory',
    keywords: ['向量', '记忆', 'embedding'],
    executeMode: 'navigate',
  },
  {
    id: 'settings-quality',
    label: '生成与质量',
    description: '质量门禁、改写与流水线运行时',
    group: '设置',
    path: '/config#generation-quality',
    keywords: ['质量', '门禁', '流水线', 'pipeline'],
    executeMode: 'navigate',
  },
  {
    id: 'settings-update',
    label: '在线更新',
    description: '检查 GitHub 官方发布并查看当前版本',
    group: '设置',
    path: '/config#software-update',
    keywords: ['更新', '升级', 'updater', 'release'],
    executeMode: 'navigate',
  },
  {
    id: 'settings-data',
    label: '系统与数据',
    description: '外观、备份、重置与桌面更新',
    group: '设置',
    path: '/config#system-data',
    keywords: ['系统', '诊断', '日志', '数据', '备份', 'system-readiness'],
    executeMode: 'navigate',
  },
  {
    id: 'nav-inspiration',
    label: '灵感工坊',
    description: '开书构思与故事蓝图',
    group: '全局',
    path: '/inspiration',
    keywords: ['灵感', '蓝图', '工坊'],
    executeMode: 'navigate',
  },
]

export function buildNavigationCommands(inProject: boolean): AppCommand[] {
  const globalCommands = GLOBAL_NAV_ITEMS.map<AppCommand>((item) => ({
    id: `nav-${item.id}`,
    label: item.label,
    description: item.id === 'create' ? '创建或导入一部作品' : `前往${item.label}`,
    group: '全局',
    path: item.path,
    keywords: [item.id],
    executeMode: 'navigate',
  }))
  if (!inProject) return [...globalCommands, ...SETTINGS_COMMANDS]
  const projectCommands = PROJECT_NAV_ITEMS.map<AppCommand>((item) => ({
    id: `nav-${item.id}`,
    label: item.label,
    description: `前往项目${item.label}中心`,
    group: '项目',
    path: item.path,
    keywords: [item.id, ...item.match],
    executeMode: 'navigate',
  }))
  return [...projectCommands, ...globalCommands, ...SETTINGS_COMMANDS]
}

export function commandFromSnapshotAction(action: SnapshotAction): AppCommand {
  const path = resolveSnapshotActionHref(action)
  return {
    id: `snapshot-${action.id}`,
    label: action.label,
    description:
      action.kind === 'intent'
        ? '前往确认页面，不会直接启动生成'
        : '处理项目建议的下一步',
    group: '下一步',
    path,
    keywords: [action.id, action.target],
    executeMode: 'navigate',
    disabled: !action.enabled,
  }
}

export function commandsFromChapters(
  chapters: ReadonlyArray<{ chapter_id: string; title?: string }>,
): AppCommand[] {
  return chapters.map((chapter) => ({
    id: `chapter-${chapter.chapter_id}`,
    label: chapter.title?.trim() || `第 ${chapter.chapter_id} 章`,
    description: `章节 ${chapter.chapter_id}`,
    group: '章节',
    path: `/writer?chapter=${encodeURIComponent(chapter.chapter_id)}`,
    keywords: ['章节', chapter.chapter_id, chapter.title || ''],
    executeMode: 'navigate',
  }))
}

export function commandsFromCharacters(
  characters: ReadonlyArray<{ id: string; name?: string }>,
): AppCommand[] {
  return characters.map((character) => ({
    id: `character-${character.id}`,
    label: character.name?.trim() || character.id,
    description: '人物设定与当前状态',
    group: '人物',
    path: `/state?character=${encodeURIComponent(character.id)}`,
    keywords: ['人物', '角色', character.id, character.name || ''],
    executeMode: 'navigate',
  }))
}

const normalize = (value: string) => value.toLocaleLowerCase().replace(/\s+/g, '')

export function searchCommands(
  commands: readonly AppCommand[],
  query: string,
  limit = 40,
): AppCommand[] {
  const needle = normalize(query)
  if (!needle) return commands.filter((command) => !command.disabled).slice(0, limit)
  return commands
    .filter((command) => !command.disabled)
    .map((command) => {
      const label = normalize(command.label)
      const description = normalize(command.description)
      const keywords = command.keywords.map(normalize)
      let score = Number.POSITIVE_INFINITY
      if (label === needle) score = 0
      else if (label.startsWith(needle)) score = 1
      else if (keywords.some((keyword) => keyword.startsWith(needle))) score = 2
      else if (label.includes(needle)) score = 3
      else if (
        description.includes(needle) ||
        keywords.some((keyword) => keyword.includes(needle))
      ) {
        score = 4
      }
      return { command, score }
    })
    .filter((entry) => Number.isFinite(entry.score))
    .sort((left, right) => left.score - right.score || left.command.label.localeCompare(right.command.label))
    .slice(0, limit)
    .map((entry) => entry.command)
}

export function commandsFromPluginNavigation(
  items: ReadonlyArray<PluginNavigationContribution>,
): AppCommand[] {
  return items.map((item) => ({
    id: `plugin-nav-${item.id}`,
    label: item.title,
    description: `打开插件：${item.plugin_name}`,
    group: item.surface === 'project_sidebar' ? '项目' : '全局',
    path: item.path,
    keywords: [item.title, item.plugin_name, item.plugin_id, item.view, '插件', '扩展'],
    executeMode: 'navigate',
  }))
}

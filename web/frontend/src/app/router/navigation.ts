export { routeFallback } from './routeMeta'

export type NavigationIcon =
  | 'library'
  | 'create'
  | 'overview'
  | 'planning'
  | 'manuscript'
  | 'production'
  | 'publishing'
  | 'settings'
  | 'extensions'

export interface NavigationItem {
  id: string
  label: string
  path: string
  icon: NavigationIcon
  match: readonly string[]
}

export const GLOBAL_NAV_ITEMS: readonly NavigationItem[] = [
  { id: 'library', label: '书库', path: '/', icon: 'library', match: ['/'] },
  { id: 'create', label: '新建作品', path: '/create', icon: 'create', match: ['/create'] },
  { id: 'settings', label: '设置', path: '/config', icon: 'settings', match: ['/config'] },
  { id: 'extensions', label: '扩展', path: '/plugins', icon: 'extensions', match: ['/plugins'] },
]

export const PROJECT_NAV_ITEMS: readonly NavigationItem[] = [
  {
    id: 'overview',
    label: '概览',
    path: '/workspace',
    icon: 'overview',
    match: ['/workspace'],
  },
  {
    id: 'planning',
    label: '策划',
    path: '/outline',
    icon: 'planning',
    match: ['/outline', '/assets', '/state', '/trope-workshop'],
  },
  {
    id: 'manuscript',
    label: '正文',
    path: '/writer',
    icon: 'manuscript',
    match: ['/writer', '/chapters'],
  },
  {
    id: 'production',
    label: '生产',
    path: '/production',
    icon: 'production',
    match: ['/production', '/monitor', '/tasks', '/pipeline', '/logs'],
  },
  {
    id: 'publishing',
    label: '发布',
    path: '/publishing',
    icon: 'publishing',
    match: ['/publishing', '/reader'],
  },
]

export function activeNavigationId(path: string, inProject: boolean): string {
  const items = inProject ? PROJECT_NAV_ITEMS : GLOBAL_NAV_ITEMS
  const match = items.find((item) =>
    item.match.some((prefix) => prefix === '/' ? path === '/' : path.startsWith(prefix)),
  )
  return match?.id ?? ''
}

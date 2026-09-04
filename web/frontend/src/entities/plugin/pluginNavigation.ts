export type PluginSurface = 'library_sidebar' | 'project_sidebar'

export interface PluginNavigationContribution {
  id: string
  plugin_id: string
  plugin_name: string
  contribution_id: string
  title: string
  surface: PluginSurface
  icon: string
  view: string
  path: string
  order: number
  default_visibility: 'visible' | 'collapsed' | 'hidden'
  requires: string[]
}

export interface PluginNavigationResponse {
  library_sidebar: PluginNavigationContribution[]
  project_sidebar: PluginNavigationContribution[]
}

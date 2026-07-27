import type { FactoryRiskAction } from '../types/factory'
import { rerunChapterGate, rewriteChapter } from '../api'

export type FactoryNavigate = (path: string) => void

export type UseFactoryActionsOptions = {
  navigate: FactoryNavigate
  onExport?: () => void
  onRun?: () => void
}

export function resolveFactoryIntent(intent: string, options: UseFactoryActionsOptions): void {
  const { navigate, onExport, onRun } = options
  if (intent === 'create' || intent === 'plan') {
    navigate('/create')
    return
  }
  if (intent === 'monitor') {
    navigate('/production?tab=runs')
    return
  }
  if (intent === 'repair') {
    navigate('/production?tab=reviews')
    return
  }
  if (intent === 'export') {
    if (onExport) {
      onExport()
      return
    }
    navigate('/workspace?tab=serialization')
    return
  }
  if (onRun) {
    onRun()
    return
  }
  navigate('/workspace?focus=pipeline')
}

export function resolveFactoryRiskAction(
  action: FactoryRiskAction,
  options: UseFactoryActionsOptions,
): void {
  if (action.intent === 'export') {
    if (options.onExport) {
      options.onExport()
      return
    }
    options.navigate('/workspace?tab=serialization')
    return
  }
  if (action.intent === 'repair') {
    options.navigate('/production?tab=reviews')
    return
  }
  if (action.intent === 'chapter' || action.route.startsWith('/chapters/')) {
    options.navigate(action.route)
    return
  }
  if (action.route) {
    options.navigate(action.route)
    return
  }
  resolveFactoryIntent(action.intent, options)
}

export async function submitFactoryRepair(chapterId: string) {
  return rewriteChapter(chapterId)
}

export async function submitFactoryRerunGate(chapterId: string) {
  return rerunChapterGate(chapterId)
}

export function useFactoryActions(options: UseFactoryActionsOptions) {
  return {
    handleFactoryIntent: (intent: string) => resolveFactoryIntent(intent, options),
    handleFactoryRiskAction: (action: FactoryRiskAction) =>
      resolveFactoryRiskAction(action, options),
    repairChapter: (chapterId: string) => submitFactoryRepair(chapterId),
    rerunGate: (chapterId: string) => submitFactoryRerunGate(chapterId),
  }
}

export function factoryCommandButtonTone(
  tone: string,
): 'primary' | 'success' | 'warning' | 'danger' | undefined {
  if (tone === 'primary') return 'primary'
  if (tone === 'success') return 'success'
  if (tone === 'warning') return 'warning'
  if (tone === 'danger') return 'danger'
  return undefined
}

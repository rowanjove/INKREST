export type CreationApproach = 'auto' | 'professional'
export type CreationSource = 'quick' | 'ai' | 'parse' | 'template'

export const CREATE_STEPS = ['工作方式', '素材来源', '写作规格', '确认建档'] as const

export function sourceRequiresModel(source: CreationSource): boolean {
  return source === 'ai' || source === 'parse'
}

export function canEnterDetails(source: CreationSource, modelReady: boolean): boolean {
  return !sourceRequiresModel(source) || modelReady
}

export function sourceMode(source: CreationSource): 'quick' | 'ai' | 'parse' {
  return source === 'template' ? 'quick' : source
}

export function nextCreateStep(
  step: number,
  options: { source: CreationSource; modelReady: boolean; hasDraft: boolean },
): number {
  if (step <= 0) return 1
  if (step === 1) return canEnterDetails(options.source, options.modelReady) ? 2 : 1
  if (step === 2) return options.hasDraft ? 3 : 2
  return 3
}

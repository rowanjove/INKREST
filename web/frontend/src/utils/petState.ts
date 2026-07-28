export type PetState =
  | 'idle'
  | 'working'
  | 'success'
  | 'error'
  | 'offline'
  | 'dragging'
  | 'question'
  | 'hide-left'
  | 'hide-right'
  | 'hide-top'
  | 'hide-bottom'

export interface PetStateContext {
  backend_health: string
  running_tasks?: Array<{ id?: string }>
  failed_tasks?: Array<{ id?: string }>
  novel_batch?: { paused?: boolean }
  pipeline_active?: boolean
  pipeline_pending?: { pending_total?: number }
}

export function isPipelineRunning(ctx: PetStateContext): boolean {
  return Boolean(ctx.pipeline_active || (ctx.running_tasks?.length ?? 0) > 0)
}

/** 需要用户立刻介入的流水线问题（修章队列积压不算紧急异常） */
export function hasPipelineProblem(
  ctx: PetStateContext,
  ignoredFailedTaskIds: string[],
): boolean {
  const activeFailed = (ctx.failed_tasks || []).filter(
    (t) => t.id && !ignoredFailedTaskIds.includes(t.id),
  )
  return activeFailed.length > 0
}

export function mapContextToPetState(
  ctx: PetStateContext | null,
  ignoredFailedTaskIds: string[],
): PetState {
  if (!ctx || ctx.backend_health !== 'ok') return 'offline'
  if (isPipelineRunning(ctx)) return 'working'
  if (hasPipelineProblem(ctx, ignoredFailedTaskIds)) return 'question'
  // 批量暂停是正常业务态，用 idle + statusLabel「全书已暂停」，不用疑惑脸
  if (ctx.novel_batch?.paused) return 'idle'
  return 'idle'
}
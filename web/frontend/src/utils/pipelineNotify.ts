/** 连写/流水线或 AI 创作任务启动后通知各窗口立刻刷新（主窗、山山宠物窗等） */
export function notifyPipelineStarted(detail?: { intent?: string; chapterId?: string }) {
  window.dispatchEvent(new CustomEvent('inkrest-pipeline-started', { detail }))
  try {
    new BroadcastChannel('inkrest-pipeline').postMessage({ type: 'started', at: Date.now(), ...detail })
  } catch {
    /* BroadcastChannel unavailable */
  }
}

/** 实时通知当前窗口正在进行直接的 AI 请求（扩写、润色、推演等） */
export function notifyAiActivity(
  active: boolean,
  detail?: { intent?: string; message?: string; chapterId?: string },
) {
  const eventName = active ? 'inkrest-ai-active' : 'inkrest-ai-idle'
  window.dispatchEvent(new CustomEvent(eventName, { detail }))
  try {
    new BroadcastChannel('inkrest-pipeline').postMessage({
      type: active ? 'ai-active' : 'ai-idle',
      at: Date.now(),
      ...detail,
    })
  } catch {
    /* BroadcastChannel unavailable */
  }
}

/** 流水线或 AI 任务执行完毕后通知 */
export function notifyPipelineFinished(success: boolean = true, detail?: { message?: string }) {
  window.dispatchEvent(new CustomEvent('inkrest-pipeline-finished', { detail: { success, ...detail } }))
  try {
    new BroadcastChannel('inkrest-pipeline').postMessage({
      type: 'finished',
      success,
      at: Date.now(),
      ...detail,
    })
  } catch {
    /* BroadcastChannel unavailable */
  }
}
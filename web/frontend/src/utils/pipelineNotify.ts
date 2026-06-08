/** 连写/流水线启动后通知各窗口立刻刷新（主窗、山山宠物窗等） */
export function notifyPipelineStarted() {
  window.dispatchEvent(new CustomEvent('inkrest-pipeline-started'))
  try {
    new BroadcastChannel('inkrest-pipeline').postMessage({ type: 'started', at: Date.now() })
  } catch {
    /* BroadcastChannel unavailable */
  }
}
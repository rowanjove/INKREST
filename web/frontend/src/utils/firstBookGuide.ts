const PENDING_KEY = 'inkrest_pending_guide'

/** 新建书成功后调用，进入工作台/大纲时弹出首次向导 */
export function markPendingFirstBookGuide(projectId: string) {
  try {
    sessionStorage.setItem(PENDING_KEY, projectId)
  } catch {
    /* ignore */
  }
}
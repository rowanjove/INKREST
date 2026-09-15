export const QUEUE_POLL_TIMEOUT_MS = 15_000
export const QUEUE_WAIT_BUDGET_MS = 600_000

export type QueueTaskClient = {
  getTask: (
    taskId: string,
    options?: { signal?: AbortSignal; timeout?: number },
  ) => Promise<{ data: { status?: string; error?: string; status_reason?: string } }>
  abortTask: (taskId: string) => Promise<unknown>
}

export async function waitForQueueTask(
  taskId: string,
  signal: AbortSignal,
  client: QueueTaskClient,
  options?: {
    now?: () => number
    delay?: (ms: number, signal: AbortSignal) => Promise<void>
    pollTimeoutMs?: number
    budgetMs?: number
  },
): Promise<{ data: { status?: string } }> {
  const now = options?.now || Date.now
  const delay = options?.delay
  const pollTimeoutMs = options?.pollTimeoutMs ?? QUEUE_POLL_TIMEOUT_MS
  const budgetMs = options?.budgetMs ?? QUEUE_WAIT_BUDGET_MS
  const startedAt = now()

  const abortAndThrow = async (message: string, name?: string) => {
    await client.abortTask(taskId).catch(() => undefined)
    const error = new Error(message)
    if (name) error.name = name
    throw error
  }

  const throwWithoutAbort = (message: string, name: string) => {
    const error = new Error(message)
    error.name = name
    throw error
  }

  const waitBeforePoll = async () => {
    if (delay) {
      await delay(1000, signal)
      return
    }
    await new Promise<void>((resolve, reject) => {
      if (signal.aborted) {
        const error = new Error('同步卷队列已取消')
        error.name = 'CanceledError'
        reject(error)
        return
      }
      let timer: ReturnType<typeof setTimeout>
      const onAbort = () => {
        clearTimeout(timer)
        const error = new Error('同步卷队列已取消')
        error.name = 'CanceledError'
        reject(error)
      }
      timer = setTimeout(() => {
        signal.removeEventListener('abort', onAbort)
        resolve()
      }, 1000)
      signal.addEventListener('abort', onAbort, { once: true })
    })
  }

  while (true) {
    if (now() - startedAt > budgetMs) {
      throwWithoutAbort(
        '同步卷队列仍在后台运行，请到生产中心或日志查看进度，不要重复提交。',
        'QueueWaitTimeoutError',
      )
    }
    if (signal.aborted) {
      await abortAndThrow('同步卷队列已取消', 'CanceledError')
    }
    let data: { status?: string; error?: string; status_reason?: string } = {}
    try {
      const response = await client.getTask(taskId, {
        signal,
        timeout: pollTimeoutMs,
      })
      data = response.data || {}
    } catch (error: any) {
      if (signal.aborted || error?.name === 'CanceledError') {
        await abortAndThrow('同步卷队列已取消', 'CanceledError')
      }
      // A single HTTP timeout/disconnect does not mean the backend task has
      // failed. Keep polling inside the total budget; only the total-budget
      // branch above is allowed to abort server-side work.
      await waitBeforePoll()
      continue
    }
    const status = String(data.status || '').toLowerCase()
    if (status === 'succeeded' || status === 'completed') return { data }
    if (status === 'failed') {
      throw new Error(
        String(data.error || data.status_reason || '同步卷队列失败，请到日志中心查看详情。'),
      )
    }
    if (status === 'cancelled' || status === 'canceled') {
      const error = new Error('同步卷队列已取消')
      error.name = 'CanceledError'
      throw error
    }
    await waitBeforePoll()
  }
}

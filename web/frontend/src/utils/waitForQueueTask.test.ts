import { describe, expect, it, vi } from 'vitest'

import { waitForQueueTask } from './waitForQueueTask'

describe('waitForQueueTask', () => {
  it('aborts the queue task when a single getTask call times out', async () => {
    const abortTask = vi.fn().mockResolvedValue({})
    const getTask = vi.fn().mockRejectedValue(new Error('timeout'))
    const controller = new AbortController()

    await expect(
      waitForQueueTask('queue-1', controller.signal, { getTask, abortTask }, {
        delay: async () => undefined,
        pollTimeoutMs: 15_000,
        budgetMs: 600_000,
      }),
    ).rejects.toThrow('同步卷队列超时')

    expect(getTask).toHaveBeenCalledWith('queue-1', {
      signal: controller.signal,
      timeout: 15_000,
    })
    expect(abortTask).toHaveBeenCalledWith('queue-1')
  })

  it('returns when the queue task succeeds', async () => {
    const abortTask = vi.fn()
    const getTask = vi.fn().mockResolvedValue({ data: { status: 'succeeded' } })
    const controller = new AbortController()

    const result = await waitForQueueTask('queue-2', controller.signal, { getTask, abortTask })
    expect(result.data.status).toBe('succeeded')
    expect(abortTask).not.toHaveBeenCalled()
  })
})

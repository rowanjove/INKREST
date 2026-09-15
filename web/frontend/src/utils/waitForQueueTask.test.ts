import { describe, expect, it, vi } from 'vitest'

import { waitForQueueTask } from './waitForQueueTask'

describe('waitForQueueTask', () => {
  it('retries a transient getTask timeout without aborting server work', async () => {
    const abortTask = vi.fn().mockResolvedValue({})
    const getTask = vi.fn()
      .mockRejectedValueOnce(new Error('timeout'))
      .mockResolvedValueOnce({ data: { status: 'succeeded' } })
    const controller = new AbortController()

    await expect(waitForQueueTask('queue-1', controller.signal, { getTask, abortTask }, {
        delay: async () => undefined,
        pollTimeoutMs: 15_000,
        budgetMs: 600_000,
      })).resolves.toEqual({ data: { status: 'succeeded' } })

    expect(getTask).toHaveBeenCalledWith('queue-1', {
      signal: controller.signal,
      timeout: 15_000,
    })
    expect(getTask).toHaveBeenCalledTimes(2)
    expect(abortTask).not.toHaveBeenCalled()
  })

  it('does not abort server work when the UI wait budget expires', async () => {
    const abortTask = vi.fn().mockResolvedValue({})
    const getTask = vi.fn().mockRejectedValue(new Error('timeout'))
    const controller = new AbortController()
    let clock = 0

    await expect(waitForQueueTask('queue-timeout', controller.signal, { getTask, abortTask }, {
      now: () => clock,
      delay: async () => { clock += 1001 },
      budgetMs: 1000,
    })).rejects.toMatchObject({
      name: 'QueueWaitTimeoutError',
      message: expect.stringContaining('仍在后台运行'),
    })

    expect(abortTask).not.toHaveBeenCalled()
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

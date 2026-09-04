import { afterEach, describe, expect, it, vi } from 'vitest'

import { sendAssistantChatStream } from './api'

describe('assistant chat stream', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('awaits the asynchronous fallback before resolving', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('stream failed')))
    let fallbackStarted = false
    let releaseFallback!: () => void
    const fallbackGate = new Promise<void>((resolve) => {
      releaseFallback = resolve
    })

    const request = sendAssistantChatStream(
      { message: '你好', history: [] },
      () => undefined,
      () => undefined,
      async () => {
        fallbackStarted = true
        await fallbackGate
      },
    )

    let requestSettled = false
    void request.then(() => {
      requestSettled = true
    })
    await Promise.resolve()
    await Promise.resolve()

    expect(fallbackStarted).toBe(true)
    expect(requestSettled).toBe(false)

    releaseFallback()
    await request
  })
})

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PluginRpcBridge } from './pluginRpc'

describe('PluginRpcBridge', () => {
  let mockIframe: any
  let postedMessages: any[] = []

  beforeEach(() => {
    postedMessages = []
    mockIframe = {
      contentWindow: {
        postMessage: (msg: any) => {
          postedMessages.push(msg)
        },
      },
    }
  })

  it('sends init message with correct session and theme payload', () => {
    const bridge = new PluginRpcBridge({
      iframe: mockIframe,
      pluginId: 'demo-plugin',
      viewId: 'demo-view',
      sessionId: 'sess_123',
      contextRevision: 1,
    })

    bridge.sendInit({
      projectId: 'proj_alpha',
      surface: 'project_sidebar',
      theme: {
        isDark: true,
        primaryColor: '#c66f4f',
        bgCard: '#1c1c20',
        textPrimary: '#f0f0f2',
      },
    })

    expect(postedMessages).toHaveLength(1)
    expect(postedMessages[0]).toMatchObject({
      type: 'inkrest:init',
      pluginId: 'demo-plugin',
      viewId: 'demo-view',
      sessionId: 'sess_123',
      projectId: 'proj_alpha',
      surface: 'project_sidebar',
    })

    bridge.destroy()
  })

  it('sendDispose resolves immediately when guest acknowledges inkrest:disposed', async () => {
    const bridge = new PluginRpcBridge({
      iframe: mockIframe,
      pluginId: 'demo-plugin',
      viewId: 'demo-view',
      sessionId: 'sess_123',
      contextRevision: 1,
    })

    const disposePromise = bridge.sendDispose('project_change', 2000)

    expect(postedMessages[0]).toMatchObject({
      type: 'inkrest:dispose',
      reason: 'project_change',
    })

    // Simulate guest reply
    bridge.onDisposed?.()

    await expect(disposePromise).resolves.toBeUndefined()
    bridge.destroy()
  })

  it('sendDispose resolves on forced timeout if guest does not acknowledge', async () => {
    vi.useFakeTimers()

    const bridge = new PluginRpcBridge({
      iframe: mockIframe,
      pluginId: 'demo-plugin',
      viewId: 'demo-view',
      sessionId: 'sess_123',
      contextRevision: 1,
    })

    const disposePromise = bridge.sendDispose('project_change', 500)

    // Fast-forward 500ms
    vi.advanceTimersByTime(500)

    await expect(disposePromise).resolves.toBeUndefined()

    bridge.destroy()
    vi.useRealTimers()
  })
})

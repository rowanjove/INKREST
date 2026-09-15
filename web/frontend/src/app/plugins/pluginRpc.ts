import { executePluginViewRpc } from '../../api'

export interface PluginThemeTokens {
  isDark: boolean
  primaryColor: string
  bgApp?: string
  bgSurface?: string
  bgCard: string
  textPrimary: string
  textMuted?: string
  border?: string
}

export interface PluginInitMessage {
  type: 'inkrest:init'
  pluginId: string
  viewId: string
  sessionId: string
  projectId?: string
  surface: 'library_sidebar' | 'project_sidebar'
  contextRevision: number
  theme: PluginThemeTokens
}

export interface PluginThemeChangeMessage {
  type: 'inkrest:theme_change'
  theme: PluginThemeTokens
}

export interface PluginDisposeMessage {
  type: 'inkrest:dispose'
  reason: 'project_change' | 'navigation' | 'user_close'
  timeoutMs: number
}

export interface PluginRpcRequestMessage {
  type: 'inkrest:rpc_request'
  requestId: string
  method: string
  params?: any
}

export interface PluginRpcResponseMessage {
  type: 'inkrest:rpc_response'
  requestId: string
  result?: any
  error?: {
    code: number
    message: string
  }
}

export type PluginHostIncomingMessage =
  | PluginRpcRequestMessage
  | { type: 'inkrest:disposed' }
  | { type: 'inkrest:ready' }

export class PluginRpcBridge {
  private iframe: HTMLIFrameElement
  private pluginId: string
  private viewId: string
  private sessionId: string
  private contextRevision: number
  private destroyed = false
  private messageListener: (event: MessageEvent) => void

  public onReady?: () => void
  public onDisposed?: () => void

  constructor(options: {
    iframe: HTMLIFrameElement
    pluginId: string
    viewId: string
    sessionId: string
    contextRevision: number
  }) {
    this.iframe = options.iframe
    this.pluginId = options.pluginId
    this.viewId = options.viewId
    this.sessionId = options.sessionId
    this.contextRevision = options.contextRevision

    this.messageListener = (event: MessageEvent) => this.handleMessage(event)
    if (typeof window !== 'undefined') {
      window.addEventListener('message', this.messageListener)
    }
  }

  public sendInit(options: {
    projectId?: string
    surface: 'library_sidebar' | 'project_sidebar'
    theme: PluginInitMessage['theme']
  }): void {
    if (this.destroyed || !this.iframe.contentWindow) return
    const msg: PluginInitMessage = {
      type: 'inkrest:init',
      pluginId: this.pluginId,
      viewId: this.viewId,
      sessionId: this.sessionId,
      projectId: options.projectId,
      surface: options.surface,
      contextRevision: this.contextRevision,
      theme: options.theme,
    }
    this.iframe.contentWindow.postMessage(msg, '*')
  }

  public sendTheme(theme: PluginThemeTokens): void {
    if (this.destroyed || !this.iframe.contentWindow) return
    const msg: PluginThemeChangeMessage = {
      type: 'inkrest:theme_change',
      theme,
    }
    this.iframe.contentWindow.postMessage(msg, '*')
  }

  public sendDispose(reason: PluginDisposeMessage['reason'], timeoutMs = 2000): Promise<void> {
    return new Promise((resolve) => {
      if (this.destroyed || !this.iframe.contentWindow) {
        resolve()
        return
      }

      let timeoutTimer: ReturnType<typeof setTimeout> | null = null

      const handleDisposed = () => {
        if (timeoutTimer) clearTimeout(timeoutTimer)
        resolve()
      }

      this.onDisposed = handleDisposed

      timeoutTimer = setTimeout(() => {
        // Forced timeout reached (2s)
        resolve()
      }, timeoutMs)

      const msg: PluginDisposeMessage = {
        type: 'inkrest:dispose',
        reason,
        timeoutMs,
      }
      this.iframe.contentWindow.postMessage(msg, '*')
    })
  }

  private async handleMessage(event: MessageEvent): Promise<void> {
    if (this.destroyed) return
    // Ensure message came from our iframe
    if (event.source !== this.iframe.contentWindow) return

    const data = event.data as PluginHostIncomingMessage
    if (!data || typeof data !== 'object') return

    if (data.type === 'inkrest:ready') {
      this.onReady?.()
      return
    }

    if (data.type === 'inkrest:disposed') {
      this.onDisposed?.()
      return
    }

    if (data.type === 'inkrest:rpc_request') {
      await this.handleRpcRequest(data)
    }
  }

  private async handleRpcRequest(req: PluginRpcRequestMessage): Promise<void> {
    if (this.destroyed || !this.iframe.contentWindow) return
    try {
      const res = await executePluginViewRpc(
        this.pluginId,
        this.viewId,
        this.sessionId,
        req.method,
        req.params,
        this.contextRevision,
      )

      if (this.destroyed || !this.iframe.contentWindow) return

      const rpcResult = res.data
      const responseMsg: PluginRpcResponseMessage = {
        type: 'inkrest:rpc_response',
        requestId: req.requestId,
        result: rpcResult?.result,
        error: rpcResult?.error,
      }
      this.iframe.contentWindow.postMessage(responseMsg, '*')
    } catch (err: any) {
      if (this.destroyed || !this.iframe.contentWindow) return
      const responseMsg: PluginRpcResponseMessage = {
        type: 'inkrest:rpc_response',
        requestId: req.requestId,
        error: {
          code: -32603,
          message: err?.response?.data?.detail || err?.message || 'RPC dispatch failed',
        },
      }
      this.iframe.contentWindow.postMessage(responseMsg, '*')
    }
  }

  public destroy(): void {
    this.destroyed = true
    if (typeof window !== 'undefined') {
      window.removeEventListener('message', this.messageListener)
    }
  }
}

import { describe, expect, it } from 'vitest'

import { wrapPluginViewHtml } from './pluginViewDocument'

describe('wrapPluginViewHtml', () => {
  it('returns empty string when the plugin did not author a view', () => {
    expect(wrapPluginViewHtml('')).toBe('')
    expect(wrapPluginViewHtml('   ')).toBe('')
  })

  it('injects the host RPC bridge without a ping demo', () => {
    const wrapped = wrapPluginViewHtml('<h2>伏笔雷达</h2><p>读取当前作品</p>')
    expect(wrapped).toContain('伏笔雷达')
    expect(wrapped).toContain('inkrest:rpc_request')
    expect(wrapped).toContain('inkrest.callRpc')
    expect(wrapped).not.toContain('测试通信')
    expect(wrapped).not.toContain('插件视图运行沙箱')
    expect(wrapped).not.toContain('host.ping')
  })

  it('replaces a plugin-authored CSP with the host policy', () => {
    const wrapped = wrapPluginViewHtml(
      '<html><head><meta http-equiv="Content-Security-Policy" content="default-src *"></head><body>ok</body></html>',
    )
    expect(wrapped).toContain("default-src 'self' data: blob:")
    expect(wrapped).not.toContain('default-src *')
  })

  it('still injects CSP when a comment mentions the header name', () => {
    const wrapped = wrapPluginViewHtml(
      '<html><!-- http-equiv="Content-Security-Policy" --><body>ok</body></html>',
    )
    expect(wrapped).toContain('http-equiv="Content-Security-Policy"')
    expect(wrapped).toContain("default-src 'self' data: blob:")
  })
})

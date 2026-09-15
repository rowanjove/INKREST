const GUEST_BRIDGE = `
<script>
  (function () {
    let reqCounter = 0;
    const pendingCalls = new Map();
    function callRpc(method, params) {
      return new Promise(function (resolve, reject) {
        const requestId = 'req_' + (++reqCounter) + '_' + Math.random().toString(36).slice(2, 8);
        pendingCalls.set(requestId, { resolve: resolve, reject: reject });
        window.parent.postMessage({
          type: 'inkrest:rpc_request',
          requestId: requestId,
          method: method,
          params: params
        }, '*');
      });
    }
    window.inkrest = window.inkrest || {};
    window.inkrest.callRpc = callRpc;
    window.addEventListener('message', function (event) {
      if (event.source !== window.parent) return;
      const data = event.data;
      if (!data || typeof data !== 'object') return;
      if (data.type === 'inkrest:rpc_response') {
        const handler = pendingCalls.get(data.requestId);
        if (!handler) return;
        pendingCalls.delete(data.requestId);
        if (data.error) handler.reject(new Error(data.error.message || 'RPC Error'));
        else handler.resolve(data.result);
      }
      if (data.type === 'inkrest:dispose') {
        window.parent.postMessage({ type: 'inkrest:disposed' }, '*');
      }
    });
    window.parent.postMessage({ type: 'inkrest:ready' }, '*');
  })();
<\/script>
`.trim()

export function wrapPluginViewHtml(html: string): string {
  const source = String(html || '').trim()
  if (!source) return ''
  const csp =
    "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self' data: blob:; script-src 'unsafe-inline' 'self'; style-src 'unsafe-inline' 'self';\"><style>html,body{margin:0;padding:0;width:100%;height:100%;background-color:transparent;color:inherit;box-sizing:border-box;}*,*::before,*::after{box-sizing:inherit;}</style>"
  if (/<html[\s>]/i.test(source)) {
    let wrapped = source.replace(/<meta[^>]+http-equiv=["']Content-Security-Policy["'][^>]*>/gi, '')
    if (/<head[\s>]/i.test(wrapped)) {
      wrapped = wrapped.replace(/<head([^>]*)>/i, `<head$1>${csp}`)
    } else {
      wrapped = wrapped.replace(/<html([^>]*)>/i, `<html$1><head>${csp}</head>`)
    }
    if (/<\/body>/i.test(wrapped)) {
      return wrapped.replace(/<\/body>/i, `${GUEST_BRIDGE}</body>`)
    }
    return `${wrapped}${GUEST_BRIDGE}`
  }
  return `<!DOCTYPE html><html><head><meta charset="utf-8">${csp}</head><body>${source}${GUEST_BRIDGE}</body></html>`
}

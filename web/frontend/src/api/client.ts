import axios from 'axios'

const isTauri = typeof window !== 'undefined' && (
  (window as any).__TAURI_METADATA__ !== undefined ||
  (window as any).__TAURI_INTERNALS__ !== undefined ||
  window.location.protocol === 'tauri:' ||
  window.location.hostname.includes('tauri')
);

const getBaseURL = () => {
  if (isTauri) {
    return 'http://127.0.0.1:8000/api';
  }
  return '/api';
};

const api = axios.create({ baseURL: getBaseURL() })

export const apiErrorMessage = (error: any, fallback = '操作失败') => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => item?.msg || item?.message || JSON.stringify(item))
      .filter(Boolean)
    if (parts.length) return parts.join('；')
  }
  if (detail && typeof detail === 'object') {
    const hint = detail.hint || detail.failure_hint
    const msg = detail.detail || detail.message
    if (hint && msg && hint !== msg) return `${msg}（${hint}）`
    if (hint) return String(hint)
    if (msg) return String(msg)
    if (detail.code) return `[${detail.code}] ${msg || hint || '请求失败'}`
    return JSON.stringify(detail)
  }
  if (error?.response?.status) return fallback
  if (typeof error?.message === 'string' && /^Request failed with status code \d+/.test(error.message)) {
    return fallback
  }
  return error?.message || fallback
}

export async function bootstrapLocalAccessToken(): Promise<void> {
  if (typeof window === 'undefined') return
  if (window.localStorage.getItem('novel-agent-access-token')) return
  try {
    const base = getBaseURL().replace(/\/api\/?$/, '')
    const response = await fetch(`${base}/api/auth/local-setup`)
    if (!response.ok) return
    const data = await response.json()
    if (data?.token) {
      window.localStorage.setItem('novel-agent-access-token', data.token)
    }
  } catch {
    // Server may not expose local token (remote bind); user can paste token manually.
  }
}

api.interceptors.request.use((config) => {
  const token = window.localStorage.getItem('novel-agent-access-token')
  if (token) config.headers['X-Novel-Agent-Token'] = token
  return config
})
api.interceptors.response.use(undefined, async (error) => {
  const config = error.config as typeof error.config & { _accessTokenRetried?: boolean }
  if (error.response?.status === 401 && config && !config._accessTokenRetried) {
    const token = window.prompt('请输入栖墨远程访问令牌')
    if (token) {
      window.localStorage.setItem('novel-agent-access-token', token)
      config._accessTokenRetried = true
      config.headers['X-Novel-Agent-Token'] = token
      return api.request(config)
    }
  }
  const message = apiErrorMessage(error, error.message)
  if (message) error.message = message
  return Promise.reject(error)
})


export default api


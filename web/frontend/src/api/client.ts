import axios from 'axios'
import { formatFailureDetail, normalizeFailureDetail } from '../utils/errorCodes'

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

async function fetchLocalAccessToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null
  try {
    const base = getBaseURL().replace(/\/api\/?$/, '')
    const response = await fetch(`${base}/api/auth/local-setup`, {
      cache: 'no-store',
      headers: { 'X-Novel-Agent-Local-Client': '1' },
    })
    if (!response.ok) return null
    const data = await response.json()
    const token = typeof data?.token === 'string' ? data.token.trim() : ''
    if (!token) return null
    window.localStorage.setItem('novel-agent-access-token', token)
    return token
  } catch {
    return null
  }
}

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
    const normalized = normalizeFailureDetail(detail, fallback)
    const formatted = formatFailureDetail(normalized)
    if (formatted) return formatted
    return JSON.stringify(detail)
  }
  if (error?.response?.status) return fallback
  if (typeof error?.message === 'string' && /^Request failed with status code \d+/.test(error.message)) {
    return fallback
  }
  return error?.message || fallback
}

export async function bootstrapLocalAccessToken(): Promise<void> {
  await fetchLocalAccessToken()
}

api.interceptors.request.use((config) => {
  const token = window.localStorage.getItem('novel-agent-access-token')
  if (token) config.headers['X-Novel-Agent-Token'] = token
  return config
})
api.interceptors.response.use(undefined, async (error) => {
  const config = error.config as typeof error.config & { _accessTokenRetried?: boolean }
  if (error.response?.status === 401 && config && !config._accessTokenRetried) {
    config._accessTokenRetried = true
    config.headers = config.headers || {}

    const localToken = await fetchLocalAccessToken()
    if (localToken) {
      config.headers['X-Novel-Agent-Token'] = localToken
      return api.request(config)
    }
    window.localStorage.removeItem('novel-agent-access-token')
  }
  const message = apiErrorMessage(error, error.message)
  if (message) error.message = message
  return Promise.reject(error)
})


export default api


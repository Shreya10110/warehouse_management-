function getApiUrl() {
  let envUrl = import.meta.env.VITE_API_URL?.trim()
  if (envUrl) {
    envUrl = envUrl.replace(/\/+$/, '')
    if (!envUrl.endsWith('/api/v1')) {
      envUrl = `${envUrl}/api/v1`
    }
    return envUrl
  }
  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname
    if (hostname.endsWith('.onrender.com')) {
      const backendHost = hostname.replace('warehouse-frontend', 'warehouse-backend')
      return `https://${backendHost}/api/v1`
    }
  }
  return 'http://127.0.0.1:8012/api/v1'
}

const API_URL = getApiUrl()

export class ApiError extends Error {
  constructor(message, status, code) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem('wms_access_token')
  const headers = { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers }
  if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })
  const contentType = response.headers.get('content-type') ?? ''
  const data = contentType.includes('application/json') ? await response.json().catch(() => ({})) : await response.text()
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    let code = 'ERROR'
    if (typeof data === 'object' && data !== null) {
      if (typeof data.detail === 'string') {
        message = data.detail
      } else if (data.detail && typeof data.detail.message === 'string') {
        message = data.detail.message
        code = data.detail.code || code
      } else if (typeof data.message === 'string') {
        message = data.message
      }
    } else if (typeof data === 'string' && data.trim().length > 0) {
      message = data.length > 200 ? `Server returned HTTP ${response.status}` : data.trim()
    }
    throw new ApiError(message, response.status, code)
  }
  return data
}

export function uploadRequest(path, file) {
  const body = new FormData()
  body.append('image', file)
  return apiRequest(path, { method: 'POST', body })
}

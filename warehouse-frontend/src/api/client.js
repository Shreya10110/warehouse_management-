const API_URL = (import.meta.env.VITE_API_URL?.trim() || 'http://127.0.0.1:8011/api/v1').replace(/\/+$/, '')

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
    const detail = data.detail ?? {}
    throw new ApiError(detail.message ?? 'Request failed. Please try again.', response.status, detail.code)
  }
  return data
}

export function uploadRequest(path, file) {
  const body = new FormData()
  body.append('image', file)
  return apiRequest(path, { method: 'POST', body })
}

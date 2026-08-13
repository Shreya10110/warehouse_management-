import { apiRequest } from './client.js'

export const authApi = {
  login: (credentials) => apiRequest('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  signup: (details) => apiRequest('/auth/signup', { method: 'POST', body: JSON.stringify(details) }),
  signupWarehouses: () => apiRequest('/auth/signup/warehouses'),
  me: () => apiRequest('/auth/me'),
  logout: () => apiRequest('/auth/logout', { method: 'POST' }),
}

import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { authApi } from '../api/auth.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('wms_access_token')))

  useEffect(() => {
    if (!localStorage.getItem('wms_access_token')) return
    authApi.me()
      .then(setUser)
      .catch(() => localStorage.removeItem('wms_access_token'))
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo(() => ({
    user,
    loading,
    async login(credentials) {
      const result = await authApi.login(credentials)
      localStorage.setItem('wms_access_token', result.access_token)
      setUser(result.user)
      return result.user
    },
    async logout() {
      try { await authApi.logout() } finally {
        localStorage.removeItem('wms_access_token')
        setUser(null)
      }
    },
  }), [user, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}

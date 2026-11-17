import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setUnauthorizedHandler, tokenStore } from '../services/api'
import type { AuthUser } from '../types/api'

interface AuthCtx {
  user: AuthUser | null
  loading: boolean
  startDemo: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
}
const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState<boolean>(!!tokenStore.get())

  const logout = useCallback(() => { tokenStore.clear(); setUser(null) }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    if (!tokenStore.get()) return
    api<AuthUser>('/auth/me').then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false))
  }, [logout])

  const accept = (r: { token: string; user: AuthUser }) => { tokenStore.set(r.token); setUser(r.user) }
  const value = useMemo<AuthCtx>(() => ({
    user, loading, logout,
    startDemo: async () => accept(await api('/auth/demo', { method: 'POST' })),
    login: async (email, password) => accept(await api('/auth/login', { method: 'POST', body: { email, password } })),
    register: async (email, password, name) => accept(await api('/auth/register', { method: 'POST', body: { email, password, display_name: name } })),
  }), [user, loading, logout])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx)
  if (!c) throw new Error('useAuth must be used inside AuthProvider')
  return c
}

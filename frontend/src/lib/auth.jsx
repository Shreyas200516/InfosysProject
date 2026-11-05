import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, setToken } from './api'

const KEY = 'sp_token'
const AuthCtx = createContext(null)

const read = () => { try { return localStorage.getItem(KEY) } catch { return null } }
const write = (t) => { try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY) } catch { /* storage unavailable: session lasts until reload */ } }

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [pendingRole, setPendingRole] = useState(null)  // staff role this person asked for and an admin has not decided yet
  const [loading, setLoading] = useState(() => !!read())

  const logout = useCallback(() => { setToken(null); write(null); setUser(null); setPendingRole(null) }, [])
  const refresh = useCallback(() => api.me().then((r) => { setUser(r.user); setPendingRole(r.pending_role || null); return r }), [])

  // Restore a saved session.
  useEffect(() => {
    const saved = read()
    if (!saved) return
    setToken(saved)
    refresh().catch(() => logout()).finally(() => setLoading(false))
  }, [logout, refresh])

  // The API reports an expired/revoked token.
  useEffect(() => {
    window.addEventListener('sp:unauthorized', logout)
    return () => window.removeEventListener('sp:unauthorized', logout)
  }, [logout])

  const accept = useCallback((res) => { setToken(res.token); write(res.token); setUser(res.user); setPendingRole(res.pending_role || null); return res.user }, [])
  const value = useMemo(() => ({
    user, loading, logout, pendingRole, refresh,
    login: async (email, password) => accept(await api.login({ email, password })),
    signup: async (payload) => accept(await api.signup(payload)),
  }), [user, loading, logout, accept, pendingRole, refresh])

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)

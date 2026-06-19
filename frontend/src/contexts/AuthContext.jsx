import { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('civitech_user')) } catch { return null }
  })
  const [loading, setLoading] = useState(false)

  const login = async (email, password) => {
    const res = await authApi.login(email, password)
    const { access_token, role, user_id, pseudo } = res.data
    const userData = { id: user_id, role, pseudo, email }
    localStorage.setItem('civitech_token', access_token)
    localStorage.setItem('civitech_user', JSON.stringify(userData))
    setUser(userData)
    return userData
  }

  const logout = () => {
    localStorage.removeItem('civitech_token')
    localStorage.removeItem('civitech_user')
    setUser(null)
  }

  const isSuperAdmin = user?.role === 'superadmin'
  const isAdmin = ['admin', 'superadmin'].includes(user?.role)
  const isModerator = ['moderator', 'admin', 'superadmin'].includes(user?.role)
  const isAmbassador = ['z_ambassador', 'moderator', 'admin', 'superadmin'].includes(user?.role)

  // Connexion directe via magic link (token déjà vérifié côté backend)
  const loginWithToken = (access_token, role, user_id, pseudo, email = '') => {
    const userData = { id: user_id, role, pseudo, email }
    localStorage.setItem('civitech_token', access_token)
    localStorage.setItem('civitech_user', JSON.stringify(userData))
    setUser(userData)
    return userData
  }

  return (
    <AuthContext.Provider value={{ user, login, loginWithToken, logout, loading, isSuperAdmin, isAdmin, isModerator, isAmbassador }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

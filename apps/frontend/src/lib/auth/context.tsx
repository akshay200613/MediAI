'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { authApi } from '@/lib/api/auth'
import apiClient from '@/lib/api/client'
import type { User } from '@/types'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<User>
  register: (email: string, password: string, fullName: string) => Promise<User>
  googleLogin: (email: string, fullName: string, requestedRole: string) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const fetchCurrentUser = async () => {
    try {
      const res = await apiClient.get('/auth/me')
      const meData = res.data?.data
      if (meData) {
        const userObj: User = {
          id: meData.id,
          email: meData.email,
          full_name: meData.full_name || meData.email,
          role: meData.role,
          domain: meData.domain || 'medai',
          is_active: true,
          is_verified: meData.is_verified ?? true,
        }
        setUser(userObj)
        if (typeof window !== 'undefined') {
          sessionStorage.setItem('user', JSON.stringify(userObj))
        }
      }
    } catch (err) {
      console.error('Failed to resolve /auth/me', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Clean up legacy localStorage auth artifacts to ensure zero fallback
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')

      const token = sessionStorage.getItem('access_token')
      const storedUser = sessionStorage.getItem('user')

      if (token) {
        if (storedUser) {
          try {
            const parsed = JSON.parse(storedUser)
            setUser(parsed)
          } catch {
            // ignore JSON parse error
          }
        }
        fetchCurrentUser()
      } else {
        setIsLoading(false)
      }
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (email: string, password: string): Promise<User> => {
    const res = await authApi.login(email, password)
    const { access_token, refresh_token } = res.data

    if (typeof window !== 'undefined') {
      sessionStorage.setItem('access_token', access_token)
      sessionStorage.setItem('refresh_token', refresh_token)
    }

    // Decode payload
    const payload = JSON.parse(atob(access_token.split('.')[1]))
    const userObj: User = {
      id: payload.sub,
      email: payload.email,
      full_name: payload.full_name || payload.email,
      role: payload.role,
      domain: 'medai',
      is_active: true,
      is_verified: true,
    }

    if (typeof window !== 'undefined') {
      sessionStorage.setItem('user', JSON.stringify(userObj))
    }
    setUser(userObj)
    return userObj
  }

  const register = async (email: string, password: string, fullName: string): Promise<User> => {
    await authApi.register(email, password, fullName)
    return await login(email, password)
  }

  const googleLogin = async (email: string, fullName: string, requestedRole: string): Promise<User> => {
    const res = await apiClient.post('/auth/google', {
      email,
      full_name: fullName,
      requested_role: requestedRole,
    })
    const { access_token, refresh_token } = res.data?.data || {}

    if (typeof window !== 'undefined') {
      sessionStorage.setItem('access_token', access_token)
      sessionStorage.setItem('refresh_token', refresh_token)
    }

    const meRes = await apiClient.get('/auth/me')
    const meData = meRes.data?.data
    const userObj: User = {
      id: meData.id,
      email: meData.email,
      full_name: meData.full_name || fullName,
      role: meData.role,
      domain: 'medai',
      is_active: true,
      is_verified: meData.is_verified,
    }

    if (typeof window !== 'undefined') {
      sessionStorage.setItem('user', JSON.stringify(userObj))
    }
    setUser(userObj)
    return userObj
  }

  const logout = () => {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('access_token')
      sessionStorage.removeItem('refresh_token')
      sessionStorage.removeItem('user')
      sessionStorage.removeItem('pending_booking_session_id')
      sessionStorage.removeItem('pending_booking_state')
    }
    try {
      const { useChatStore } = require('@/lib/hooks/useChatStore')
      useChatStore.getState().resetStore()
    } catch {}
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, login, register, googleLogin, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

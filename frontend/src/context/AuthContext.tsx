import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../utils/supabase'
import { UserRole } from '../types/auth'

interface AuthUser {
  id: string
  email: string
  role: UserRole
  permissions: string[]
  organization_id: number | null
  full_name: string | null
  username: string
  is_verified: boolean
}

interface AuthContextType {
  user: AuthUser | null
  session: Session | null
  isAuthenticated: boolean
  isLoading: boolean       // true only while login() is in progress
  isInitializing: boolean  // true while startup session check is running
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (permission: string) => boolean
  hasRole: (...roles: UserRole[]) => boolean
  isAdmin: boolean
  isSuperAdmin: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

// Fetch the PostgreSQL user profile using the Supabase JWT
async function fetchUserProfile(accessToken: string): Promise<AuthUser | null> {
  try {
    const res = await fetch('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(false)       // true only during login()
  const [isInitializing, setIsInitializing] = useState(true) // true during startup session check

  // Load initial session and subscribe to auth state changes
  useEffect(() => {
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      setSession(session)
      if (session?.access_token) {
        const profile = await fetchUserProfile(session.access_token)
        setUser(profile)
      }
      setIsInitializing(false)
    }).catch(() => {
      // Supabase unreachable (e.g. env vars not set) — let the app load anyway
      setIsInitializing(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        setSession(session)
        if (session?.access_token) {
          const profile = await fetchUserProfile(session.access_token)
          setUser(profile)
        } else {
          setUser(null)
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
      // onAuthStateChange will set session + user
    } finally {
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    await supabase.auth.signOut()
    setUser(null)
    setSession(null)
  }, [])

  const hasPermission = useCallback(
    (permission: string) => user?.permissions?.includes(permission) ?? false,
    [user]
  )

  const hasRole = useCallback(
    (...roles: UserRole[]) => (user ? roles.includes(user.role) : false),
    [user]
  )

  return (
    <AuthContext.Provider value={{
      user,
      session,
      isAuthenticated: !!user,
      isLoading,
      isInitializing,
      login,
      logout,
      hasPermission,
      hasRole,
      isAdmin: user ? ['super_admin', 'admin'].includes(user.role) : false,
      isSuperAdmin: user ? user.role === 'super_admin' : false,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

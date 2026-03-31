import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { Session } from '@supabase/supabase-js'
import toast from 'react-hot-toast'
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
  isAuthenticated: boolean   // true when Supabase session exists (independent of backend profile)
  isLoading: boolean         // true only while login() is in progress
  isInitializing: boolean    // true while startup session check is running
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (permission: string) => boolean
  hasRole: (...roles: UserRole[]) => boolean
  isAdmin: boolean
  isSuperAdmin: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

async function fetchUserProfile(accessToken: string): Promise<AuthUser | null> {
  try {
    const res = await fetch('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    if (!res.ok) {
      console.warn('[Auth] Profile fetch failed:', res.status)
      return null
    }
    return await res.json()
  } catch (err) {
    console.warn('[Auth] Profile fetch error:', err)
    return null
  }
}

// Resolves after ms milliseconds with a fallback value
function withTimeout<T>(promise: Promise<T>, ms: number, fallback: T): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>(resolve => setTimeout(() => resolve(fallback), ms)),
  ])
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isInitializing, setIsInitializing] = useState(true)

  useEffect(() => {
    // 3-second timeout so a broken Supabase config never blocks the UI forever
    withTimeout(
      supabase.auth.getSession(),
      3000,
      { data: { session: null }, error: null }
    ).then(async ({ data: { session } }) => {
      setSession(session)
      if (session?.access_token) {
        const profile = await fetchUserProfile(session.access_token)
        setUser(profile)
      }
    }).catch(err => {
      console.error('[Auth] getSession error:', err)
    }).finally(() => {
      setIsInitializing(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        console.log('[Auth] state change:', _event, !!session)
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
    console.log('[Auth] login attempt:', email)
    setIsLoading(true)
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password })
      console.log('[Auth] signInWithPassword result:', { user: data?.user?.email, error: error?.message })
      if (error) {
        toast.error(error.message)
        throw error
      }
      toast.success('Welcome back!')
      // onAuthStateChange fires automatically — sets session + fetches profile
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

  // isAuthenticated is based on Supabase session, NOT backend profile fetch.
  // This ensures that a working Supabase setup lets users reach the dashboard
  // even if the backend /auth/me endpoint is temporarily unavailable.
  const isAuthenticated = !!session

  return (
    <AuthContext.Provider value={{
      user,
      session,
      isAuthenticated,
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

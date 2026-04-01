import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, AuthToken } from '../types'
import { api } from '../services/api'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  fetchCurrentUser: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await api.post<AuthToken>(
            '/api/v1/auth/token',
            new URLSearchParams({ username, password }),
            { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
          )

          const { access_token } = response.data
          set({ token: access_token, isAuthenticated: true })

          // Fetch user info
          await get().fetchCurrentUser()
        } catch (error: any) {
          const message = error.response?.data?.detail || 'Login failed'
          set({ error: message, isAuthenticated: false })
          throw error
        } finally {
          set({ isLoading: false })
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        })
      },

      fetchCurrentUser: async () => {
        try {
          const response = await api.get<User>('/api/v1/auth/me')
          set({ user: response.data })
        } catch (error) {
          set({ user: null, isAuthenticated: false, token: null })
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'sira-auth',
      // H6: token is NOT persisted to localStorage — it lives in memory only.
      // Persisting JWTs to localStorage exposes them to XSS token theft.
      // isAuthenticated is persisted only to restore UI state on page refresh;
      // the actual token is re-obtained via /refresh or re-login as needed.
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the api module used by authStore
vi.mock('../services/api', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

// Reset zustand store state between tests by clearing localStorage
beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  // Clear the zustand module cache so each test gets a fresh store
  vi.resetModules()
})

describe('authStore', () => {
  describe('initial state', () => {
    it('starts unauthenticated with no user or token', async () => {
      const { useAuthStore } = await import('../stores/authStore')
      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.token).toBeNull()
      expect(state.user).toBeNull()
      expect(state.error).toBeNull()
    })
  })

  describe('login', () => {
    it('sets token and isAuthenticated on successful login', async () => {
      const { api } = await import('../services/api')
      const mockPost = vi.mocked(api.post)
      const mockGet = vi.mocked(api.get)

      mockPost.mockResolvedValueOnce({ data: { access_token: 'test-token-abc' } })
      mockGet.mockResolvedValueOnce({
        data: { id: 1, username: 'alice', role: 'operator' },
      })

      const { useAuthStore } = await import('../stores/authStore')
      await useAuthStore.getState().login('alice', 'Password@1')

      const state = useAuthStore.getState()
      expect(state.token).toBe('test-token-abc')
      expect(state.isAuthenticated).toBe(true)
      expect(state.user).toEqual({ id: 1, username: 'alice', role: 'operator' })
    })

    it('sets error and stays unauthenticated on failed login', async () => {
      const { api } = await import('../services/api')
      const mockPost = vi.mocked(api.post)

      const error = Object.assign(new Error('Unauthorized'), {
        response: { data: { detail: 'Incorrect username or password' } },
      })
      mockPost.mockRejectedValueOnce(error)

      const { useAuthStore } = await import('../stores/authStore')
      await expect(useAuthStore.getState().login('alice', 'wrong')).rejects.toThrow()

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.token).toBeNull()
      expect(state.error).toBe('Incorrect username or password')
    })

    it('clears error on each new login attempt', async () => {
      const { api } = await import('../services/api')
      const mockPost = vi.mocked(api.post)
      const mockGet = vi.mocked(api.get)

      // First login: fail
      mockPost.mockRejectedValueOnce(
        Object.assign(new Error(), { response: { data: { detail: 'Bad creds' } } })
      )
      const { useAuthStore } = await import('../stores/authStore')
      try { await useAuthStore.getState().login('alice', 'bad') } catch {}
      expect(useAuthStore.getState().error).toBe('Bad creds')

      // Second login: succeed
      mockPost.mockResolvedValueOnce({ data: { access_token: 'tok' } })
      mockGet.mockResolvedValueOnce({ data: { id: 1, username: 'alice' } })
      await useAuthStore.getState().login('alice', 'Good@Pass1')
      expect(useAuthStore.getState().error).toBeNull()
    })
  })

  describe('logout', () => {
    it('clears all auth state', async () => {
      const { api } = await import('../services/api')
      vi.mocked(api.post).mockResolvedValueOnce({ data: { access_token: 'tok' } })
      vi.mocked(api.get).mockResolvedValueOnce({ data: { id: 1, username: 'alice' } })

      const { useAuthStore } = await import('../stores/authStore')
      await useAuthStore.getState().login('alice', 'Password@1')
      expect(useAuthStore.getState().isAuthenticated).toBe(true)

      useAuthStore.getState().logout()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.token).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.error).toBeNull()
    })
  })

  describe('fetchCurrentUser', () => {
    it('populates user on success', async () => {
      const { api } = await import('../services/api')
      vi.mocked(api.get).mockResolvedValueOnce({
        data: { id: 5, username: 'bob', role: 'admin' },
      })

      const { useAuthStore } = await import('../stores/authStore')
      await useAuthStore.getState().fetchCurrentUser()

      expect(useAuthStore.getState().user).toEqual({ id: 5, username: 'bob', role: 'admin' })
    })

    it('clears auth state when request fails', async () => {
      const { api } = await import('../services/api')
      vi.mocked(api.get).mockRejectedValueOnce(new Error('Network error'))

      const { useAuthStore } = await import('../stores/authStore')
      // Seed some state first
      useAuthStore.setState({ token: 'old-token', isAuthenticated: true })

      await useAuthStore.getState().fetchCurrentUser()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.token).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })

  describe('clearError', () => {
    it('sets error to null', async () => {
      const { useAuthStore } = await import('../stores/authStore')
      useAuthStore.setState({ error: 'Some error' })
      useAuthStore.getState().clearError()
      expect(useAuthStore.getState().error).toBeNull()
    })
  })
})

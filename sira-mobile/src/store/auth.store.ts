/**
 * Auth Store — Zustand store for authentication state
 */
import { create } from 'zustand';
import { login, logout, getCurrentUser, LoginRequest, CurrentUser } from '../api/auth';
import { tokenStorage } from '../api/client';

interface AuthState {
  user: CurrentUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  loadCurrentUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState & AuthActions>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      await login(credentials);
      const user = await getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (err: any) {
      set({
        isLoading: false,
        error: err?.response?.data?.detail ?? 'Login failed',
      });
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      await logout();
    } finally {
      set({ user: null, isAuthenticated: false, isLoading: false, error: null });
    }
  },

  loadCurrentUser: async () => {
    const token = tokenStorage.getString('access_token');
    if (!token) {
      set({ isAuthenticated: false });
      return;
    }
    try {
      const user = await getCurrentUser();
      set({ user, isAuthenticated: true });
    } catch {
      set({ isAuthenticated: false });
    }
  },

  clearError: () => set({ error: null }),
}));

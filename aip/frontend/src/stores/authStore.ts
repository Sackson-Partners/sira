import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi } from '../services/api';

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  organization?: string;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  b2cLogin: (b2cToken: string) => Promise<void>;
  logout: () => void;
  loadMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const { data } = await authApi.login(email, password);
        localStorage.setItem('aip_token', data.access_token);
        set({
          token: data.access_token,
          refreshToken: data.refresh_token,
          user: {
            id: data.user_id,
            email: data.email,
            full_name: data.full_name,
            role: data.role,
            is_active: true,
          },
          isAuthenticated: true,
        });
      },

      b2cLogin: async (b2cToken) => {
        const { data } = await authApi.b2cLogin(b2cToken);
        localStorage.setItem('aip_token', data.access_token);
        set({
          token: data.access_token,
          refreshToken: data.refresh_token,
          user: {
            id: data.user_id,
            email: data.email,
            full_name: data.full_name,
            role: data.role,
            is_active: true,
          },
          isAuthenticated: true,
        });
      },

      logout: () => {
        localStorage.removeItem('aip_token');
        set({ token: null, refreshToken: null, user: null, isAuthenticated: false });
      },

      loadMe: async () => {
        try {
          const { data } = await authApi.me();
          set({ user: data, isAuthenticated: true });
        } catch {
          get().logout();
        }
      },
    }),
    {
      name: 'aip-auth',
      partialize: (s) => ({ token: s.token, refreshToken: s.refreshToken, user: s.user, isAuthenticated: s.isAuthenticated }),
    }
  )
);

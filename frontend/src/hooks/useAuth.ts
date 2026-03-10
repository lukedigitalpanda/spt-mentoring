import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../utils/api';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchCurrentUser: () => Promise<void>;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const { data } = await api.post('/auth/token/', { email, password });
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        // Fetch user profile
        const { data: user } = await api.get('/users/me/');
        set({ user, isAuthenticated: true });
      },

      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, isAuthenticated: false });
      },

      fetchCurrentUser: async () => {
        try {
          const { data } = await api.get('/users/me/');
          set({ user: data, isAuthenticated: true });
        } catch {
          set({ user: null, isAuthenticated: false });
        }
      },
    }),
    { name: 'auth-store', partialize: (s) => ({ user: s.user, isAuthenticated: s.isAuthenticated }) }
  )
);

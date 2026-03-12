import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { User } from '../types';
import api from './api';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchCurrentUser: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  hydrate: async () => {
    try {
      const token = await SecureStore.getItemAsync('access_token');
      if (token) {
        const { data } = await api.get<User>('/users/me/');
        set({ user: data, isAuthenticated: true });
      }
    } catch {
      // Token invalid – clear
      await SecureStore.deleteItemAsync('access_token');
      await SecureStore.deleteItemAsync('refresh_token');
    } finally {
      set({ isLoading: false });
    }
  },

  login: async (email, password) => {
    const { data } = await api.post<{ access: string; refresh: string }>(
      '/auth/token/',
      { email, password }
    );
    await SecureStore.setItemAsync('access_token', data.access);
    await SecureStore.setItemAsync('refresh_token', data.refresh);
    const me = await api.get<User>('/users/me/');
    set({ user: me.data, isAuthenticated: true });
  },

  logout: async () => {
    await SecureStore.deleteItemAsync('access_token');
    await SecureStore.deleteItemAsync('refresh_token');
    set({ user: null, isAuthenticated: false });
  },

  fetchCurrentUser: async () => {
    const { data } = await api.get<User>('/users/me/');
    set({ user: data });
  },
}));

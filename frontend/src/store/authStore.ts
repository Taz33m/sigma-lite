import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  authReady: boolean;
  setUser: (user: User | null) => void;
  setAuthReady: (ready: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      authReady: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setAuthReady: (ready) => set({ authReady: ready }),
      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, isAuthenticated: false, authReady: true });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isAuthenticated = false;
          state.authReady = false;
        }
      },
    }
  )
);

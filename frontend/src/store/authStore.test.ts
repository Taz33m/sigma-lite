import { beforeEach, describe, expect, it } from 'vitest';
import { useAuthStore } from './authStore';
import type { User } from '@/types';

const mockUser: User = {
  id: 1,
  email: 'test@example.com',
  username: 'tester',
  is_active: true,
  is_superuser: false,
  created_at: '2026-01-01T00:00:00Z',
};

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isAuthenticated: false, authReady: false });
    localStorage.clear();
  });

  it('starts unauthenticated', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.authReady).toBe(false);
  });

  it('marks the user authenticated when setUser is called', () => {
    useAuthStore.getState().setUser(mockUser);
    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.isAuthenticated).toBe(true);
  });

  it('logout clears the user', () => {
    localStorage.setItem('access_token', 'token');
    localStorage.setItem('refresh_token', 'refresh');
    useAuthStore.getState().setUser(mockUser);
    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.authReady).toBe(true);
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('setUser(null) is treated as unauthenticated', () => {
    useAuthStore.getState().setUser(mockUser);
    useAuthStore.getState().setUser(null);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('tracks verified auth bootstrap readiness separately from persisted state', () => {
    useAuthStore.getState().setAuthReady(true);
    expect(useAuthStore.getState().authReady).toBe(true);
  });
});

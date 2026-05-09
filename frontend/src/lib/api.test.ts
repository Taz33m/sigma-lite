import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { InternalAxiosRequestConfig } from 'axios';
import { attachAuthToken } from './api';

describe('axios instance', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('does not attach Authorization when no token is stored', async () => {
    const config = attachAuthToken({
      headers: {},
    } as InternalAxiosRequestConfig);
    expect(config.headers.Authorization).toBeUndefined();
  });

  it('attaches a Bearer token from localStorage', async () => {
    localStorage.setItem('access_token', 'abc123');
    const config = attachAuthToken({
      headers: {},
    } as InternalAxiosRequestConfig);
    expect(config.headers.Authorization).toBe('Bearer abc123');
  });
});

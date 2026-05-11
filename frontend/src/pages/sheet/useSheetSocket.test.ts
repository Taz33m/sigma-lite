import { afterEach, describe, expect, it, vi } from 'vitest';
import { buildCollaborateUrl, parseCommittedCellUpdate } from './useSheetSocket';

describe('buildCollaborateUrl', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('uses VITE_WS_URL when explicitly configured', () => {
    vi.stubEnv('VITE_WS_URL', 'wss://collab.example.com/');
    vi.stubEnv('VITE_API_URL', 'https://api.example.com');

    expect(buildCollaborateUrl(42, 'ticket with spaces')).toBe(
      'wss://collab.example.com/ws/collaborate/42?ticket=ticket%20with%20spaces'
    );
  });

  it('derives the WebSocket origin from VITE_API_URL by default', () => {
    vi.stubEnv('VITE_WS_URL', '');
    vi.stubEnv('VITE_API_URL', 'https://api.example.com');

    expect(buildCollaborateUrl(3, 'abc123')).toBe(
      'wss://api.example.com/ws/collaborate/3?ticket=abc123'
    );
  });
});

describe('parseCommittedCellUpdate', () => {
  it('normalizes committed cell update broadcasts', () => {
    expect(
      parseCommittedCellUpdate({
        type: 'cell_update',
        user_id: 7,
        username: 'editor',
        row_index: 3,
        column: 'city',
        value: 'Boston',
        formula: null,
        version: 4,
        timestamp: '2026-05-11T13:00:00Z',
      })
    ).toEqual({
      user_id: 7,
      username: 'editor',
      row_index: 3,
      column: 'city',
      value: 'Boston',
      formula: null,
      version: 4,
      timestamp: '2026-05-11T13:00:00Z',
    });
  });

  it('rejects malformed or non-cell messages', () => {
    expect(parseCommittedCellUpdate({ type: 'comment', text: 'hi' })).toBeNull();
    expect(
      parseCommittedCellUpdate({
        type: 'cell_update',
        row_index: 3,
        column: 'city',
      })
    ).toBeNull();
  });
});

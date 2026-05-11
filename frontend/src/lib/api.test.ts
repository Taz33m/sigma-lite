import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { AxiosAdapter, InternalAxiosRequestConfig } from 'axios';
import api, { attachAuthToken, datasetAPI, sheetAPI } from './api';

const originalAdapter = api.defaults.adapter;

describe('axios instance', () => {
  beforeEach(() => {
    localStorage.clear();
    api.defaults.adapter = originalAdapter;
  });

  afterEach(() => {
    localStorage.clear();
    api.defaults.adapter = originalAdapter;
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

describe('public-beta API clients', () => {
  const requests: InternalAxiosRequestConfig[] = [];

  beforeEach(() => {
    requests.length = 0;
    api.defaults.adapter = (async (config) => {
      requests.push(config);
      let data: unknown = {};

      if (config.url?.endsWith('/query')) {
        data = { data: [], total_rows: 0, page: 1, page_size: 25, total_pages: 0 };
      } else if (config.url?.endsWith('/cell')) {
        data = { row_index: 1, column: 'age', value: '42', version: 3 };
      } else if (config.url?.endsWith('/formula-preview')) {
        data = { valid: true, value: 95, formula: '=SUM(age)', error: null };
      } else if (config.url?.endsWith('/ws-ticket')) {
        data = { ticket: 'one-time-ticket', expires_at: '2026-05-11T13:00:00Z' };
      } else if (config.url?.endsWith('/export')) {
        data = new Blob(['name,age\nAlice,30\n'], { type: 'text/csv' });
      } else if (config.url?.endsWith('/shares')) {
        data = [{ id: 0, sheet_id: 7, user_id: 1, username: 'owner', email: 'owner@example.com', role: 'owner' }];
      } else if (config.url?.includes('/shares/')) {
        data = undefined;
      }

      return {
        data,
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      };
    }) as AxiosAdapter;
  });

  afterEach(() => {
    api.defaults.adapter = originalAdapter;
  });

  it('posts dataset query filters, sort, and pagination to the query endpoint', async () => {
    const response = await datasetAPI.query(11, {
      filters: [{ column: 'age', operator: 'gt', value: '30' }],
      logic: 'and',
      sort: { column: 'salary', direction: 'desc' },
      page: 2,
      page_size: 25,
    });

    expect(response.total_rows).toBe(0);
    expect(requests[0].method).toBe('post');
    expect(requests[0].url).toBe('/api/datasets/11/query');
    expect(JSON.parse(requests[0].data as string)).toEqual({
      filters: [{ column: 'age', operator: 'gt', value: '30' }],
      logic: 'and',
      sort: { column: 'salary', direction: 'desc' },
      page: 2,
      page_size: 25,
    });
  });

  it('posts sheet-scoped query and aggregate requests through sheet endpoints', async () => {
    await sheetAPI.query(7, {
      filters: [{ column: 'city', operator: 'eq', value: 'NYC' }],
      logic: 'and',
      sort: { column: 'age', direction: 'desc' },
      page: 1,
      page_size: 50,
    });
    await sheetAPI.aggregate(7, {
      column: 'age',
      operation: 'sum',
      filters: [{ column: 'city', operator: 'eq', value: 'NYC' }],
      logic: 'and',
    });

    expect(requests.map((request) => `${request.method} ${request.url}`)).toEqual([
      'post /api/sheets/7/query',
      'post /api/sheets/7/aggregate',
    ]);
    expect(JSON.parse(requests[0].data as string)).toEqual({
      filters: [{ column: 'city', operator: 'eq', value: 'NYC' }],
      logic: 'and',
      sort: { column: 'age', direction: 'desc' },
      page: 1,
      page_size: 50,
    });
    expect(JSON.parse(requests[1].data as string)).toEqual({
      column: 'age',
      operation: 'sum',
      filters: [{ column: 'city', operator: 'eq', value: 'NYC' }],
      logic: 'and',
    });
  });

  it('sends optimistic cell versions and force overwrites to the sheet cell endpoint', async () => {
    const response = await sheetAPI.updateCell(7, {
      row_index: 1,
      column: 'age',
      value: '42',
      expected_version: 2,
      force: true,
    });

    expect(response.version).toBe(3);
    expect(requests[0].method).toBe('patch');
    expect(requests[0].url).toBe('/api/sheets/7/cell');
    expect(JSON.parse(requests[0].data as string)).toEqual({
      row_index: 1,
      column: 'age',
      value: '42',
      expected_version: 2,
      force: true,
    });
  });

  it('calls formula preview without persisting a cell update', async () => {
    const response = await sheetAPI.previewFormula(7, {
      row_index: 1,
      column: 'age',
      value: '=SUM(age)',
    });

    expect(response).toMatchObject({ valid: true, value: 95, formula: '=SUM(age)' });
    expect(requests[0].method).toBe('post');
    expect(requests[0].url).toBe('/api/sheets/7/formula-preview');
  });

  it('requests one-time WebSocket collaboration tickets', async () => {
    const response = await sheetAPI.createWebSocketTicket(7);

    expect(response.ticket).toBe('one-time-ticket');
    expect(requests[0].method).toBe('post');
    expect(requests[0].url).toBe('/api/sheets/7/ws-ticket');
    expect(JSON.parse(requests[0].data as string)).toEqual({});
  });

  it('requests streamed sheet exports as blobs', async () => {
    const response = await sheetAPI.export(7, {
      format: 'xlsx',
      filters: [{ column: 'department', operator: 'eq', value: 'Engineering' }],
      logic: 'and',
      sort: { column: 'name', direction: 'asc' },
      include_comments: true,
      include_charts: false,
    });

    expect(response).toBeInstanceOf(Blob);
    expect(requests[0].method).toBe('post');
    expect(requests[0].url).toBe('/api/sheets/7/export');
    expect(requests[0].responseType).toBe('blob');
    expect(JSON.parse(requests[0].data as string)).toEqual({
      format: 'xlsx',
      filters: [{ column: 'department', operator: 'eq', value: 'Engineering' }],
      logic: 'and',
      sort: { column: 'name', direction: 'asc' },
      include_comments: true,
      include_charts: false,
    });
  });

  it('covers share list, create, and delete endpoints', async () => {
    await sheetAPI.listShares(7);
    await sheetAPI.createShare(7, { username_or_email: 'teammate@example.com', role: 'viewer' });
    await sheetAPI.deleteShare(7, 9);

    expect(requests.map((request) => `${request.method} ${request.url}`)).toEqual([
      'get /api/sheets/7/shares',
      'post /api/sheets/7/shares',
      'delete /api/sheets/7/shares/9',
    ]);
    expect(JSON.parse(requests[1].data as string)).toEqual({
      username_or_email: 'teammate@example.com',
      role: 'viewer',
    });
  });
});

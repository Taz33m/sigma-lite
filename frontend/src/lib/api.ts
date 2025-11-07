import axios from 'axios';
import type {
  LoginCredentials,
  RegisterData,
  AuthTokens,
  User,
  Dataset,
  DatasetData,
  FilterQuery,
  AggregateRequest,
  AggregateResult,
  Sheet,
  SheetCreate,
  Chart,
  ChartCreate,
} from '@/types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/api/auth/refresh`, {
            token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: async (data: RegisterData): Promise<User> => {
    const response = await api.post('/api/auth/register', data);
    return response.data;
  },

  login: async (credentials: LoginCredentials): Promise<AuthTokens> => {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await api.post('/api/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// Dataset API
export const datasetAPI = {
  upload: async (name: string, file: File, description?: string): Promise<Dataset> => {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);
    if (description) {
      formData.append('description', description);
    }

    const response = await api.post('/api/datasets', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  list: async (): Promise<Dataset[]> => {
    const response = await api.get('/api/datasets');
    return response.data;
  },

  get: async (id: number): Promise<Dataset> => {
    const response = await api.get(`/api/datasets/${id}`);
    return response.data;
  },

  getData: async (id: number, page = 1, pageSize = 100): Promise<DatasetData> => {
    const response = await api.get(`/api/datasets/${id}/data`, {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  filter: async (id: number, query: FilterQuery): Promise<DatasetData> => {
    const response = await api.post(`/api/datasets/${id}/filter`, query);
    return response.data;
  },

  aggregate: async (id: number, request: AggregateRequest): Promise<AggregateResult> => {
    const response = await api.post(`/api/datasets/${id}/aggregate`, request);
    return response.data;
  },

  update: async (id: number, data: Partial<Dataset>): Promise<Dataset> => {
    const response = await api.put(`/api/datasets/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/datasets/${id}`);
  },
};

// Sheet API
export const sheetAPI = {
  create: async (data: SheetCreate): Promise<Sheet> => {
    const response = await api.post('/api/sheets', data);
    return response.data;
  },

  list: async (datasetId?: number): Promise<Sheet[]> => {
    const response = await api.get('/api/sheets', {
      params: datasetId ? { dataset_id: datasetId } : {},
    });
    return response.data;
  },

  get: async (id: number): Promise<Sheet> => {
    const response = await api.get(`/api/sheets/${id}`);
    return response.data;
  },

  update: async (id: number, data: Partial<Sheet>): Promise<Sheet> => {
    const response = await api.put(`/api/sheets/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/sheets/${id}`);
  },
};

// Chart API
export const chartAPI = {
  create: async (data: ChartCreate): Promise<Chart> => {
    const response = await api.post('/api/charts', data);
    return response.data;
  },

  list: async (sheetId?: number): Promise<Chart[]> => {
    const response = await api.get('/api/charts', {
      params: sheetId ? { sheet_id: sheetId } : {},
    });
    return response.data;
  },

  get: async (id: number): Promise<Chart> => {
    const response = await api.get(`/api/charts/${id}`);
    return response.data;
  },

  update: async (id: number, data: Partial<Chart>): Promise<Chart> => {
    const response = await api.put(`/api/charts/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/charts/${id}`);
  },
};

export default api;

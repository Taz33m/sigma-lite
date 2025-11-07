export interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Dataset {
  id: number;
  name: string;
  description?: string;
  file_name: string;
  file_size: number;
  row_count: number;
  column_count: number;
  schema?: DatasetSchema;
  owner_id: number;
  created_at: string;
  updated_at?: string;
}

export interface DatasetSchema {
  columns: ColumnInfo[];
  row_count: number;
  column_count: number;
}

export interface ColumnInfo {
  name: string;
  type: string;
  semantic_type: 'numeric' | 'text' | 'datetime';
  nullable: boolean;
  unique_count: number;
  sample_values: any[];
  min?: number;
  max?: number;
  mean?: number;
}

export interface DatasetData {
  data: Record<string, any>[];
  total_rows: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FilterRequest {
  column: string;
  operator: 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'contains' | 'startswith' | 'endswith';
  value: any;
}

export interface FilterQuery {
  filters: FilterRequest[];
  logic: 'and' | 'or';
  page: number;
  page_size: number;
}

export interface AggregateRequest {
  column: string;
  operation: 'sum' | 'avg' | 'min' | 'max' | 'count' | 'median';
  group_by?: string[];
}

export interface AggregateResult {
  result?: any;
  group_results?: Record<string, any>[];
}

export interface Sheet {
  id: number;
  name: string;
  description?: string;
  dataset_id: number;
  owner_id: number;
  config?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface SheetCreate {
  name: string;
  description?: string;
  dataset_id: number;
  config?: Record<string, any>;
}

export interface Chart {
  id: number;
  name: string;
  chart_type: 'line' | 'bar' | 'scatter' | 'pie';
  sheet_id: number;
  owner_id: number;
  config: ChartConfig;
  created_at: string;
  updated_at?: string;
}

export interface ChartConfig {
  x_axis?: string;
  y_axis?: string | string[];
  labels?: string;
  values?: string;
  title?: string;
  colors?: string[];
  [key: string]: any;
}

export interface ChartCreate {
  name: string;
  chart_type: 'line' | 'bar' | 'scatter' | 'pie';
  sheet_id: number;
  config: ChartConfig;
}

export interface WebSocketMessage {
  type: 'connected' | 'user_joined' | 'user_left' | 'cell_update' | 'cursor_move' | 'selection' | 'comment';
  user_id?: number;
  username?: string;
  active_users?: Array<{ user_id: number; username: string }>;
  [key: string]: any;
}

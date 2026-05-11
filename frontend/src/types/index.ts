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

export interface CellUpdateRequest {
  row_index: number;
  column: string;
  value: any;
  expected_version?: number;
  force?: boolean;
}

export interface CellUpdateResult {
  row_index: number;
  column: string;
  value: any;
  formula?: string | null;
  version?: number;
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

export interface SortRequest {
  column: string;
  direction: 'asc' | 'desc';
}

export interface DatasetQuery {
  filters: FilterRequest[];
  logic: 'and' | 'or';
  sort?: SortRequest | null;
  page: number;
  page_size: number;
}

export interface AggregateRequest {
  column: string;
  operation: 'sum' | 'avg' | 'min' | 'max' | 'count' | 'median';
  group_by?: string[];
  filters?: FilterRequest[];
  logic?: 'and' | 'or';
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
  access_role: 'owner' | 'editor' | 'viewer';
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

export interface CommentCreate {
  text: string;
  row_index?: number | null;
  column?: string | null;
}

export interface SheetComment {
  id: number;
  sheet_id: number;
  owner_id: number;
  username: string;
  text: string;
  row_index?: number | null;
  column?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface FormulaPreviewRequest {
  row_index: number;
  column: string;
  value: string;
}

export interface FormulaPreviewResult {
  valid: boolean;
  value?: any;
  formula?: string | null;
  error?: string | null;
}

export interface SheetExportRequest {
  format: 'csv' | 'xlsx' | 'pdf';
  filters: FilterRequest[];
  logic: 'and' | 'or';
  sort?: SortRequest | null;
  include_comments?: boolean;
  include_charts?: boolean;
}

export interface SheetShare {
  id: number;
  sheet_id: number;
  user_id: number;
  username: string;
  email?: string;
  role: 'owner' | 'editor' | 'viewer';
  created_at: string;
  updated_at?: string;
}

export interface SheetShareCreate {
  username_or_email: string;
  role: 'editor' | 'viewer';
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
  query?: {
    filters: FilterRequest[];
    logic: 'and' | 'or';
    sort?: SortRequest | null;
    page_size: number;
  };
  [key: string]: any;
}

export interface ChartCreate {
  name: string;
  chart_type: 'line' | 'bar' | 'scatter' | 'pie';
  sheet_id: number;
  config: ChartConfig;
}

export interface WebSocketTicketResponse {
  ticket: string;
  expires_at: string;
}

export interface WebSocketMessage {
  type:
    | 'connected'
    | 'user_joined'
    | 'user_left'
    | 'cell_update'
    | 'cursor_move'
    | 'selection'
    | 'comment'
    | 'error'
    | 'access_revoked';
  user_id?: number;
  username?: string;
  active_users?: Array<{ user_id: number; username: string }>;
  [key: string]: any;
}

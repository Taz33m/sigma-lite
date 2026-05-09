import type { ChartCreate, FilterRequest } from '@/types';

export type SheetViewConfig = {
  filters?: FilterRequest[];
  filterLogic?: 'and' | 'or';
  pageSize?: number;
  chartDraft?: Partial<ChartCreate>;
};

export type ActiveUser = {
  user_id: number;
  username: string;
};

export type SelectedCell = {
  rowIndex: number;
  column: string;
};

export type CollaborationComment = {
  id?: number;
  username: string;
  text: string;
  timestamp?: string;
  row_index?: number | null;
  column?: string | null;
};

export type CursorActivity = {
  username: string;
  row?: number;
  column?: string;
};

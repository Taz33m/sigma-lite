import type { GridColDef } from '@mui/x-data-grid';

export type DatasetGridRow = Record<string, unknown> & {
  __row_id: number;
  __source_index?: number;
};

export function buildDatasetGridRows(
  data: Record<string, unknown>[] = []
): DatasetGridRow[] {
  return data.map((row, index) => ({ ...row, __row_id: index }));
}

export function buildDatasetGridColumns(
  data: Record<string, unknown>[] = []
): GridColDef[] {
  const firstRow = data[0];
  if (!firstRow) {
    return [];
  }

  return Object.keys(firstRow)
    .filter((key) => !key.startsWith('__'))
    .map((key) => ({
      field: key,
      headerName: key,
      width: 150,
      editable: true,
    }));
}

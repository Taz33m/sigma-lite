import { Button, Chip, Paper, Stack, Typography } from '@mui/material';
import {
  Dataset,
  FileDownload,
  FilterAlt,
  People,
  Save,
  TableChart,
} from '@mui/icons-material';
import {
  DataGrid,
  type GridColDef,
  type GridPaginationModel,
  type GridRowModel,
} from '@mui/x-data-grid';
import type { Dataset as DatasetRecord, Sheet } from '@/types';
import type { DatasetGridRow } from '@/lib/datasetGrid';

export function SheetSummaryBar({
  dataset,
  sheet,
  activeCount,
  filterCount,
  rowCountLabel,
  onSave,
  onExport,
  saving,
  canExport,
}: {
  dataset?: DatasetRecord;
  sheet?: Sheet;
  activeCount: number;
  filterCount: number;
  rowCountLabel: string;
  onSave: () => void;
  onExport: () => void;
  saving: boolean;
  canExport: boolean;
}) {
  return (
    <Paper sx={{ p: 2 }}>
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={2}
        alignItems={{ xs: 'flex-start', md: 'center' }}
      >
        <Chip icon={<Dataset />} label={dataset?.file_name || 'Dataset'} />
        <Chip label={rowCountLabel} />
        <Chip label={`${dataset?.column_count || 0} columns`} />
        <Chip icon={<TableChart />} label="Saved sheet" color="primary" />
        <Chip icon={<People />} label={`${activeCount} active`} variant="outlined" />
        {filterCount > 0 && (
          <Chip
            icon={<FilterAlt />}
            label={`${filterCount} active filter${filterCount === 1 ? '' : 's'}`}
            color="secondary"
          />
        )}
        <Button
          variant="outlined"
          startIcon={<Save />}
          disabled={!sheet || saving}
          onClick={onSave}
        >
          {saving ? 'Saving...' : 'Save View'}
        </Button>
        <Button
          variant="outlined"
          startIcon={<FileDownload />}
          disabled={!canExport}
          onClick={onExport}
        >
          Export CSV
        </Button>
      </Stack>
      {sheet?.description && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          {sheet.description}
        </Typography>
      )}
    </Paper>
  );
}

export function DataGridPanel({
  rows,
  columns,
  rowCount,
  loading,
  paginationModel,
  onPaginationModelChange,
  processRowUpdate,
  onProcessRowUpdateError,
  onCellSelect,
}: {
  rows: DatasetGridRow[];
  columns: GridColDef[];
  rowCount: number;
  loading: boolean;
  paginationModel: GridPaginationModel;
  onPaginationModelChange: (model: GridPaginationModel) => void;
  processRowUpdate: (
    newRow: GridRowModel<DatasetGridRow>,
    oldRow: GridRowModel<DatasetGridRow>
  ) => Promise<GridRowModel<DatasetGridRow>>;
  onProcessRowUpdateError: (error: unknown) => void;
  onCellSelect: (rowIndex: number, column: string) => void;
}) {
  return (
    <Paper sx={{ height: 660, flex: 1, minWidth: 0 }}>
      <DataGrid
        rows={rows}
        columns={columns}
        getRowId={(row) => row.__row_id}
        paginationMode="server"
        rowCount={rowCount}
        loading={loading}
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationModelChange}
        pageSizeOptions={[10, 25, 50, 100]}
        processRowUpdate={processRowUpdate}
        onProcessRowUpdateError={onProcessRowUpdateError}
        onCellClick={(params) => {
          const rowIndex = Number(params.row.__source_index ?? params.row.__row_id);
          onCellSelect(rowIndex, params.field);
        }}
        disableRowSelectionOnClick
      />
    </Paper>
  );
}

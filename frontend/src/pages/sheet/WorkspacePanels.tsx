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
  type GridSortModel,
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
  onExportXlsx,
  onExportPdf,
  saving,
  canExport,
  canEdit,
}: {
  dataset?: DatasetRecord;
  sheet?: Sheet;
  activeCount: number;
  filterCount: number;
  rowCountLabel: string;
  onSave: () => void;
  onExport: () => void;
  onExportXlsx: () => void;
  onExportPdf: () => void;
  saving: boolean;
  canExport: boolean;
  canEdit: boolean;
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        px: 2,
        py: 1.5,
        borderRadius: 1,
        boxShadow: 'none',
      }}
    >
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={1.25}
        alignItems={{ xs: 'flex-start', md: 'center' }}
        flexWrap="wrap"
        useFlexGap
      >
        <Chip size="small" icon={<Dataset />} label={dataset?.file_name || 'Dataset'} />
        <Chip size="small" label={rowCountLabel} />
        <Chip size="small" label={`${dataset?.column_count || 0} columns`} />
        <Chip size="small" icon={<TableChart />} label="Saved sheet" color="primary" />
        <Chip size="small" icon={<People />} label={`${activeCount} active`} variant="outlined" />
        {filterCount > 0 && (
          <Chip
            size="small"
            icon={<FilterAlt />}
            label={`${filterCount} active filter${filterCount === 1 ? '' : 's'}`}
            color="secondary"
          />
        )}
        <Button
          variant="outlined"
          startIcon={<Save />}
          disabled={!sheet || saving || !canEdit}
          onClick={onSave}
          size="small"
        >
          {saving ? 'Saving...' : 'Save View'}
        </Button>
        <Button
          variant="outlined"
          startIcon={<FileDownload />}
          disabled={!canExport}
          onClick={onExportXlsx}
          size="small"
        >
          XLSX
        </Button>
        <Button
          variant="outlined"
          startIcon={<FileDownload />}
          disabled={!canExport}
          onClick={onExportPdf}
          size="small"
        >
          PDF
        </Button>
        <Button
          variant="outlined"
          startIcon={<FileDownload />}
          disabled={!canExport}
          onClick={onExport}
          size="small"
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
  sortModel,
  onPaginationModelChange,
  onSortModelChange,
  processRowUpdate,
  onProcessRowUpdateError,
  onCellSelect,
}: {
  rows: DatasetGridRow[];
  columns: GridColDef[];
  rowCount: number;
  loading: boolean;
  paginationModel: GridPaginationModel;
  sortModel: GridSortModel;
  onPaginationModelChange: (model: GridPaginationModel) => void;
  onSortModelChange: (model: GridSortModel) => void;
  processRowUpdate: (
    newRow: GridRowModel<DatasetGridRow>,
    oldRow: GridRowModel<DatasetGridRow>
  ) => Promise<GridRowModel<DatasetGridRow>>;
  onProcessRowUpdateError: (error: unknown) => void;
  onCellSelect: (rowIndex: number, column: string) => void;
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        height: { xs: 560, lg: '100%' },
        flex: 1,
        minWidth: 0,
        overflow: 'hidden',
        borderRadius: 1,
        boxShadow: 'none',
      }}
    >
      <DataGrid
        rows={rows}
        columns={columns}
        getRowId={(row) => row.__row_id}
        paginationMode="server"
        sortingMode="server"
        rowCount={rowCount}
        loading={loading}
        paginationModel={paginationModel}
        sortModel={sortModel}
        onPaginationModelChange={onPaginationModelChange}
        onSortModelChange={onSortModelChange}
        pageSizeOptions={[10, 25, 50, 100]}
        processRowUpdate={processRowUpdate}
        onProcessRowUpdateError={onProcessRowUpdateError}
        density="compact"
        rowHeight={42}
        columnHeaderHeight={44}
        sx={{
          border: 0,
          '& .MuiDataGrid-columnHeaders': {
            backgroundColor: 'grey.50',
          },
          '& .MuiDataGrid-cell': {
            borderColor: 'grey.200',
          },
          '& .MuiDataGrid-footerContainer': {
            minHeight: 46,
          },
        }}
        onCellClick={(params) => {
          const rowIndex = Number(params.row.__source_index ?? params.row.__row_id);
          onCellSelect(rowIndex, params.field);
        }}
        disableRowSelectionOnClick
      />
    </Paper>
  );
}

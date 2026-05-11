import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Paper,
  IconButton,
  CircularProgress,
  Alert,
  Stack,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Tabs,
  Tab,
} from '@mui/material';
import {
  ArrowBack,
  Calculate,
  FilterAlt,
  Save,
  Send,
} from '@mui/icons-material';
import {
  type GridColDef,
  type GridRowModel,
  type GridPaginationModel,
  type GridSortModel,
} from '@mui/x-data-grid';
import { chartAPI, datasetAPI, sheetAPI } from '@/lib/api';
import {
  buildDatasetGridColumns,
  buildDatasetGridRows,
  type DatasetGridRow,
} from '@/lib/datasetGrid';
import { ChartPreview, SavedChartCard } from '@/pages/sheet/ChartPreview';
import { DataGridPanel, SheetSummaryBar } from '@/pages/sheet/WorkspacePanels';
import { formatCommittedCellUpdateToast } from '@/pages/sheet/realtime';
import { useSheetSocket } from '@/pages/sheet/useSheetSocket';
import { useAuthStore } from '@/store/authStore';
import type {
  CollaborationComment,
  SelectedCell,
  SheetViewConfig,
} from '@/pages/sheet/types';
import type {
  AggregateRequest,
  AggregateResult,
  Chart as SavedChart,
  ChartCreate,
  FilterRequest,
  SheetShare,
} from '@/types';

const filterOperators: FilterRequest['operator'][] = [
  'eq',
  'ne',
  'gt',
  'lt',
  'gte',
  'lte',
  'contains',
  'startswith',
  'endswith',
];

const aggregateOperations: AggregateRequest['operation'][] = [
  'sum',
  'avg',
  'min',
  'max',
  'count',
  'median',
];

const chartTypes: ChartCreate['chart_type'][] = ['bar', 'line', 'scatter', 'pie'];
type InspectorTab = 'filters' | 'summary' | 'fields' | 'comments' | 'charts' | 'access';

type CellConflict = {
  rowIndex: number;
  column: string;
  currentValue: unknown;
  currentVersion: number;
  attemptedValue: unknown;
};

export default function SheetPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sheetId = Number(id);
  const currentUser = useAuthStore((state) => state.user);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [sortModel, setSortModel] = useState<GridSortModel>([]);
  const [filterLogic, setFilterLogic] = useState<'and' | 'or'>('and');
  const [filters, setFilters] = useState<FilterRequest[]>([]);
  const [filterDraft, setFilterDraft] = useState<FilterRequest>({
    column: '',
    operator: 'eq',
    value: '',
  });
  const [aggregateDraft, setAggregateDraft] = useState<AggregateRequest>({
    column: '',
    operation: 'sum',
  });
  const [aggregateResult, setAggregateResult] = useState<AggregateResult | null>(null);
  const [selectedCell, setSelectedCell] = useState<SelectedCell | null>(null);
  const [commentDraft, setCommentDraft] = useState('');
  const [chartDraft, setChartDraft] = useState<ChartCreate>({
    name: 'New chart',
    chart_type: 'bar',
    sheet_id: sheetId,
    config: {
      x_axis: '',
      y_axis: '',
    },
  });
  const [hydratedSheetId, setHydratedSheetId] = useState<number | null>(null);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('filters');
  const [fieldSearch, setFieldSearch] = useState('');
  const [shareTarget, setShareTarget] = useState('');
  const [shareRole, setShareRole] = useState<'editor' | 'viewer'>('viewer');
  const [cellConflict, setCellConflict] = useState<CellConflict | null>(null);
  const {
    activeUsers,
    activeUserCount,
    cursorActivity,
    realtimeComments,
    lastCellUpdate,
    sendSocketMessage,
  } = useSheetSocket(Number.isFinite(sheetId) ? sheetId : undefined);

  const {
    data: sheet,
    isLoading: isSheetLoading,
    isError: isSheetError,
  } = useQuery({
    queryKey: ['sheet', id],
    queryFn: () => sheetAPI.get(sheetId),
    enabled: Number.isFinite(sheetId),
  });

  const {
    data: dataset,
    isLoading: isDatasetLoading,
    isError: isDatasetError,
  } = useQuery({
    queryKey: ['dataset', sheet?.dataset_id],
    queryFn: () => datasetAPI.get(sheet!.dataset_id),
    enabled: Boolean(sheet?.dataset_id),
  });

  const {
    data: datasetData,
    isLoading: isDataLoading,
    isError: isDataError,
  } = useQuery({
    queryKey: [
      'sheet-data',
      sheet?.dataset_id,
      paginationModel.page,
      paginationModel.pageSize,
      filterLogic,
      JSON.stringify(filters),
      JSON.stringify(sortModel),
    ],
    queryFn: () =>
      sheetAPI.query(sheet!.id, {
        filters,
        logic: filterLogic,
        sort: sortModel[0]?.field
          ? {
              column: sortModel[0].field,
              direction: sortModel[0].sort === 'desc' ? 'desc' : 'asc',
            }
          : null,
        page: paginationModel.page + 1,
        page_size: paginationModel.pageSize,
      }),
    enabled: Boolean(sheet?.dataset_id),
  });

  const { data: charts = [] } = useQuery({
    queryKey: ['charts', sheetId],
    queryFn: () => chartAPI.list(sheetId),
    enabled: Number.isFinite(sheetId),
  });

  const { data: persistedComments = [] } = useQuery({
    queryKey: ['comments', sheetId],
    queryFn: () => sheetAPI.listComments(sheetId),
    enabled: Number.isFinite(sheetId),
  });

  const { data: shares = [] } = useQuery({
    queryKey: ['shares', sheetId],
    queryFn: () => sheetAPI.listShares(sheetId),
    enabled: Number.isFinite(sheetId) && sheet?.access_role === 'owner',
  });

  const rows = buildDatasetGridRows(datasetData?.data);
  const currentRole = sheet?.access_role || 'viewer';
  const canEdit = currentRole === 'owner' || currentRole === 'editor';
  const canManageShares = currentRole === 'owner';
  const commentAnchors = useMemo(
    () =>
      new Set(
        persistedComments
          .filter((comment) => comment.row_index !== null && comment.column)
          .map((comment) => `${comment.row_index}:${comment.column}`)
      ),
    [persistedComments]
  );
  const columns: GridColDef[] = useMemo(() => {
    const baseColumns = datasetData?.data.length
      ? buildDatasetGridColumns(datasetData.data)
      : dataset?.schema?.columns.map((column) => ({
          field: column.name,
          headerName: column.name,
          width: 150,
          editable: true,
        })) || [];

    return baseColumns.map((column) => ({
      ...column,
      editable: canEdit,
      renderCell: (params) => {
        const sourceIndex = params.row.__source_index ?? params.row.__row_id;
        const hasComment = commentAnchors.has(`${sourceIndex}:${params.field}`);
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, minWidth: 0 }}>
            {hasComment && (
              <Box
                aria-label="Cell has comments"
                sx={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  bgcolor: 'warning.main',
                  flexShrink: 0,
                }}
              />
            )}
            <Typography variant="body2" noWrap>
              {String(params.value ?? '')}
            </Typography>
          </Box>
        );
      },
    }));
  }, [canEdit, commentAnchors, dataset?.schema?.columns, datasetData?.data]);
  const schemaColumns = dataset?.schema?.columns || [];
  const numericColumns = schemaColumns.filter(
    (column) => column.semantic_type === 'numeric'
  );
  const filteredSchemaColumns = schemaColumns.filter((column) => {
    const needle = fieldSearch.trim().toLowerCase();
    if (!needle) {
      return true;
    }
    return `${column.name} ${column.semantic_type} ${column.type}`
      .toLowerCase()
      .includes(needle);
  });
  const isLoading = isSheetLoading || isDatasetLoading;
  const isError =
    isSheetError || isDatasetError || isDataError || !Number.isFinite(sheetId);

  const aggregateMutation = useMutation({
    mutationFn: (request: AggregateRequest) =>
      sheetAPI.aggregate(sheet!.id, request),
    onSuccess: (result) => {
      setAggregateResult(result);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Aggregation failed');
    },
  });

  const saveViewMutation = useMutation({
    mutationFn: () =>
      sheetAPI.update(sheet!.id, {
        config: {
          filters,
          filterLogic,
          pageSize: paginationModel.pageSize,
          sortModel,
          chartDraft,
        },
      }),
    onSuccess: () => {
      toast.success('View saved');
      queryClient.invalidateQueries({ queryKey: ['sheet', id] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Could not save view');
    },
  });

  const createChartMutation = useMutation({
    mutationFn: (chart: ChartCreate) => chartAPI.create(chart),
    onSuccess: () => {
      toast.success('Chart saved');
      queryClient.invalidateQueries({ queryKey: ['charts', sheetId] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Could not save chart');
    },
  });

  const createCommentMutation = useMutation({
    mutationFn: (comment: { text: string; row_index?: number; column?: string }) =>
      sheetAPI.createComment(sheetId, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', sheetId] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Could not save comment');
    },
  });

  const updateCellMutation = useMutation({
    mutationFn: ({
      rowIndex,
      column,
      value,
      expectedVersion,
      force,
    }: {
      rowIndex: number;
      column: string;
      value: unknown;
      expectedVersion?: number;
      force?: boolean;
    }) => sheetAPI.updateCell(sheet!.id, {
      row_index: rowIndex,
      column,
      value,
      expected_version: expectedVersion,
      force,
    }),
    onSuccess: () => {
      toast.success('Cell saved');
      setCellConflict(null);
      queryClient.invalidateQueries({ queryKey: ['sheet-data'] });
      queryClient.invalidateQueries({ queryKey: ['dataset', sheet?.dataset_id] });
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail;
      if (error.response?.status === 409 && detail) {
        setCellConflict({
          rowIndex: detail.row_index,
          column: detail.column,
          currentValue: detail.current_value,
          currentVersion: detail.current_version,
          attemptedValue: detail.attempted_value,
        });
        toast.error('Cell changed elsewhere');
        return;
      }
      toast.error(detail || 'Could not save cell');
    },
  });

  const createShareMutation = useMutation({
    mutationFn: () =>
      sheetAPI.createShare(sheetId, {
        username_or_email: shareTarget.trim(),
        role: shareRole,
      }),
    onSuccess: () => {
      toast.success('Access updated');
      setShareTarget('');
      queryClient.invalidateQueries({ queryKey: ['shares', sheetId] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Could not update access');
    },
  });

  const deleteShareMutation = useMutation({
    mutationFn: (share: SheetShare) => sheetAPI.deleteShare(sheetId, share.id),
    onSuccess: () => {
      toast.success('Access removed');
      queryClient.invalidateQueries({ queryKey: ['shares', sheetId] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Could not remove access');
    },
  });

  const addFilter = () => {
    const column = filterDraft.column || schemaColumns[0]?.name;
    if (!column) {
      return;
    }

    setFilters((current) => [
      ...current,
      {
        column,
        operator: filterDraft.operator,
        value: filterDraft.value,
      },
    ]);
    setPaginationModel((current) => ({ ...current, page: 0 }));
    setFilterDraft((current) => ({ ...current, column, value: '' }));
  };

  const clearFilters = () => {
    setFilters([]);
    setPaginationModel((current) => ({ ...current, page: 0 }));
  };

  useEffect(() => {
    if (!sheet || hydratedSheetId === sheet.id) {
      return;
    }

    const config = sheet.config as SheetViewConfig | undefined;
    if (config?.filters) {
      setFilters(config.filters);
    }
    if (config?.filterLogic) {
      setFilterLogic(config.filterLogic);
    }
    if (config?.pageSize) {
      setPaginationModel((current) => ({
        ...current,
        page: 0,
        pageSize: config.pageSize || current.pageSize,
      }));
    }
    if (config?.sortModel) {
      setSortModel(config.sortModel);
    }
    if (config?.chartDraft) {
      setChartDraft((current) => ({
        ...current,
        ...config.chartDraft,
        sheet_id: sheet.id,
        config: {
          ...current.config,
          ...config.chartDraft?.config,
        },
      }));
    }

    setHydratedSheetId(sheet.id);
  }, [hydratedSheetId, sheet]);

  useEffect(() => {
    if (!lastCellUpdate || !sheet?.dataset_id) {
      return;
    }
    const updateMessage = formatCommittedCellUpdateToast(lastCellUpdate, currentUser?.id);
    if (updateMessage) {
      toast(updateMessage);
    }
    queryClient.invalidateQueries({ queryKey: ['sheet-data'] });
    queryClient.invalidateQueries({ queryKey: ['dataset', sheet.dataset_id] });
  }, [currentUser?.id, lastCellUpdate, queryClient, sheet?.dataset_id]);

  const processRowUpdate = async (
    newRow: GridRowModel<DatasetGridRow>,
    oldRow: GridRowModel<DatasetGridRow>
  ) => {
    const changedColumn = Object.keys(newRow).find(
      (key) => !key.startsWith('__') && newRow[key] !== oldRow[key]
    );

    if (!changedColumn || !sheet || !canEdit) {
      return oldRow;
    }

    const sourceIndex = Number(
      newRow.__source_index ??
        paginationModel.page * paginationModel.pageSize + newRow.__row_id
    );
    const nextValue = newRow[changedColumn];
    if (typeof nextValue === 'string' && nextValue.trim().startsWith('=')) {
      const preview = await sheetAPI.previewFormula(sheet.id, {
        row_index: sourceIndex,
        column: changedColumn,
        value: nextValue,
      });
      if (!preview.valid) {
        throw new Error(preview.error || 'Invalid formula');
      }
    }
    await updateCellMutation.mutateAsync({
      rowIndex: sourceIndex,
      column: changedColumn,
      value: nextValue,
      expectedVersion: oldRow.__cell_versions?.[changedColumn],
    });

    return newRow;
  };

  const sendComment = () => {
    if (!canEdit) {
      return;
    }
    const text = commentDraft.trim();
    if (!text) {
      return;
    }

    createCommentMutation.mutate({
      text,
      row_index: selectedCell?.rowIndex,
      column: selectedCell?.column,
    });
    setCommentDraft('');
  };

  const visibleComments: CollaborationComment[] = [
    ...persistedComments.map((comment) => ({
      id: comment.id,
      username: comment.username,
      text: comment.text,
      timestamp: comment.created_at,
      row_index: comment.row_index,
      column: comment.column,
    })),
    ...realtimeComments,
  ].filter(
    (comment, index, allComments) =>
      comment.id === undefined ||
      allComments.findIndex((candidate) => candidate.id === comment.id) === index
  );

  const selectedCellComments = selectedCell
    ? visibleComments.filter(
        (comment) =>
          comment.row_index === selectedCell.rowIndex &&
          comment.column === selectedCell.column
      )
    : [];
  const displayedComments = selectedCellComments.length
    ? selectedCellComments
    : visibleComments.slice(-5);

  const runAggregation = () => {
    const column = aggregateDraft.column || numericColumns[0]?.name;
    if (!column) {
      return;
    }

    aggregateMutation.mutate({
      ...aggregateDraft,
      column,
      group_by: aggregateDraft.group_by?.length ? aggregateDraft.group_by : undefined,
      filters,
      logic: filterLogic,
    });
    setAggregateDraft((current) => ({ ...current, column }));
  };

  const saveChart = () => {
    if (!canEdit) {
      return;
    }
    const xField = chartDraft.config.x_axis || schemaColumns[0]?.name;
    const yField = chartDraft.config.y_axis || numericColumns[0]?.name;
    if (!sheet || !xField || !yField) {
      return;
    }

    createChartMutation.mutate({
      ...chartDraft,
      sheet_id: sheet.id,
        config: {
          ...chartDraft.config,
          x_axis: String(xField),
          y_axis: String(yField),
          labels: String(xField),
          values: String(yField),
          query: {
            filters,
            logic: filterLogic,
            sort: sortModel[0]?.field
              ? {
                  column: sortModel[0].field,
                  direction: sortModel[0].sort === 'desc' ? 'desc' : 'asc',
                }
              : null,
            page_size: 1000,
          },
        },
      });
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportSheet = async (format: 'csv' | 'xlsx' | 'pdf') => {
    if (!sheet) {
      return;
    }
    try {
      const blob = await sheetAPI.export(sheet.id, {
        format,
        filters,
        logic: filterLogic,
        sort: sortModel[0]?.field
          ? {
              column: sortModel[0].field,
              direction: sortModel[0].sort === 'desc' ? 'desc' : 'asc',
            }
          : null,
        include_comments: true,
        include_charts: true,
      });
      downloadBlob(blob, `${sheet.name || 'sheet'}-export.${format}`);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Export failed');
    }
  };

  const previewChart: SavedChart | null = sheet
    ? {
        id: 0,
        name: chartDraft.name,
        chart_type: chartDraft.chart_type,
        sheet_id: sheet.id,
        owner_id: sheet.owner_id,
        config: chartDraft.config,
        created_at: '',
      }
    : null;

  return (
    <Box
      sx={{
        height: { xs: 'auto', lg: '100vh' },
        minHeight: '100vh',
        overflow: { xs: 'auto', lg: 'hidden' },
        bgcolor: 'grey.50',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <AppBar
        position="static"
        elevation={0}
        sx={{
          bgcolor: 'background.paper',
          color: 'text.primary',
          borderBottom: 1,
          borderColor: 'divider',
        }}
      >
        <Toolbar variant="dense" sx={{ minHeight: 56 }}>
          <IconButton
            edge="start"
            color="inherit"
            onClick={() => navigate(dataset ? `/dataset/${dataset.id}` : '/')}
            sx={{ mr: 1.5 }}
          >
            <ArrowBack />
          </IconButton>
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Typography variant="subtitle1" fontWeight={700} noWrap>
              {sheet?.name || 'Sheet'}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap component="div">
              {dataset?.name}
            </Typography>
          </Box>
        </Toolbar>
      </AppBar>

      <Box
        sx={{
          flex: 1,
          minHeight: { xs: 'auto', lg: 0 },
          p: { xs: 1.5, lg: 2 },
          display: 'flex',
          flexDirection: 'column',
          gap: 1.5,
        }}
      >
        {isLoading ? (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
            }}
          >
            <CircularProgress />
          </Box>
        ) : isError ? (
          <Alert severity="error">Unable to load this sheet.</Alert>
        ) : (
          <>
            <SheetSummaryBar
              dataset={dataset}
              sheet={sheet}
              activeCount={activeUserCount || activeUsers.length}
              filterCount={filters.length}
              rowCountLabel={`${(dataset?.row_count || 0).toLocaleString()} rows`}
              saving={saveViewMutation.isPending}
              canExport={rows.length > 0}
              canEdit={canEdit}
              onSave={() => saveViewMutation.mutate()}
              onExport={() => exportSheet('csv')}
              onExportXlsx={() => exportSheet('xlsx')}
              onExportPdf={() => exportSheet('pdf')}
            />

            {cellConflict && (
              <Alert
                severity="warning"
                action={
                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      onClick={() => {
                        setCellConflict(null);
                        queryClient.invalidateQueries({ queryKey: ['sheet-data'] });
                      }}
                    >
                      Reload Current
                    </Button>
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => {
                        updateCellMutation.mutate({
                          rowIndex: cellConflict.rowIndex,
                          column: cellConflict.column,
                          value: cellConflict.attemptedValue,
                          expectedVersion: cellConflict.currentVersion,
                          force: true,
                        });
                      }}
                    >
                      Overwrite
                    </Button>
                  </Stack>
                }
              >
                {cellConflict.column} row {cellConflict.rowIndex + 1} changed to{' '}
                {String(cellConflict.currentValue ?? '')}.
              </Alert>
            )}

            <Box
              sx={{
                flex: 1,
                minHeight: { xs: 'auto', lg: 0 },
                display: 'flex',
                gap: 1.5,
                flexDirection: { xs: 'column', lg: 'row' },
              }}
            >
              <DataGridPanel
                rows={rows}
                columns={columns}
                rowCount={datasetData?.total_rows || 0}
                loading={isDataLoading}
                paginationModel={paginationModel}
                sortModel={sortModel}
                onPaginationModelChange={setPaginationModel}
                onSortModelChange={(model) => {
                  setSortModel(model);
                  setPaginationModel((current) => ({ ...current, page: 0 }));
                }}
                processRowUpdate={processRowUpdate}
                onProcessRowUpdateError={(error) => {
                  toast.error(error instanceof Error ? error.message : 'Cell update failed');
                }}
                onCellSelect={(rowIndex, column) => {
                  setSelectedCell({ rowIndex, column });
                  sendSocketMessage({
                    type: 'cursor_move',
                    row: rowIndex,
                    column,
                  });
                }}
              />

              <Paper
                variant="outlined"
                sx={{
                  width: { xs: '100%', lg: 380 },
                  flexShrink: 0,
                  height: { xs: 520, lg: '100%' },
                  minHeight: 0,
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column',
                  borderRadius: 1,
                  boxShadow: 'none',
                }}
              >
                <Tabs
                  value={inspectorTab}
                  onChange={(_, value) => setInspectorTab(value as InspectorTab)}
                  variant="fullWidth"
                  sx={{
                    minHeight: 44,
                    borderBottom: 1,
                    borderColor: 'divider',
                    '& .MuiTab-root': {
                      minHeight: 44,
                      minWidth: 0,
                      px: 0.75,
                      fontSize: '0.78rem',
                      textTransform: 'none',
                      fontWeight: 700,
                    },
                  }}
                >
                  <Tab value="filters" label="Filters" />
                  <Tab value="summary" label="Summary" />
                  <Tab value="fields" label="Fields" />
                  <Tab value="comments" label="Comments" />
                  <Tab value="charts" label="Charts" />
                  <Tab value="access" label="Access" />
                </Tabs>

                <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', p: 2 }}>
                  {inspectorTab === 'filters' && (
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={700}>
                          Filters
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Narrow the current sheet without leaving the grid.
                        </Typography>
                      </Box>

                      <FormControl fullWidth size="small">
                        <InputLabel id="filter-column-label">Column</InputLabel>
                        <Select
                          labelId="filter-column-label"
                          label="Column"
                          value={filterDraft.column}
                          onChange={(event) =>
                            setFilterDraft((current) => ({
                              ...current,
                              column: event.target.value,
                            }))
                          }
                        >
                          {schemaColumns.map((column) => (
                            <MenuItem key={column.name} value={column.name}>
                              {column.name}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>

                      <Stack direction="row" spacing={1}>
                        <FormControl size="small" sx={{ width: 118 }}>
                          <InputLabel id="filter-logic-label">Logic</InputLabel>
                          <Select
                            labelId="filter-logic-label"
                            label="Logic"
                            value={filterLogic}
                            onChange={(event) => {
                              setFilterLogic(event.target.value as 'and' | 'or');
                              setPaginationModel((current) => ({ ...current, page: 0 }));
                            }}
                          >
                            <MenuItem value="and">AND</MenuItem>
                            <MenuItem value="or">OR</MenuItem>
                          </Select>
                        </FormControl>
                        <FormControl size="small" sx={{ flex: 1 }}>
                          <InputLabel id="filter-operator-label">Operator</InputLabel>
                          <Select
                            labelId="filter-operator-label"
                            label="Operator"
                            value={filterDraft.operator}
                            onChange={(event) =>
                              setFilterDraft((current) => ({
                                ...current,
                                operator: event.target.value as FilterRequest['operator'],
                              }))
                            }
                          >
                            {filterOperators.map((operator) => (
                              <MenuItem key={operator} value={operator}>
                                {operator}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Stack>

                      <TextField
                        size="small"
                        label="Value"
                        value={String(filterDraft.value)}
                        onChange={(event) =>
                          setFilterDraft((current) => ({
                            ...current,
                            value: event.target.value,
                          }))
                        }
                      />

                      <Stack direction="row" spacing={1}>
                        <Button
                          variant="contained"
                          startIcon={<FilterAlt />}
                          onClick={addFilter}
                          disabled={!schemaColumns.length}
                        >
                          Add
                        </Button>
                        <Button onClick={clearFilters} disabled={!filters.length}>
                          Clear
                        </Button>
                      </Stack>

                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {filters.length ? (
                          filters.map((filter, index) => (
                            <Chip
                              key={`${filter.column}-${filter.operator}-${index}`}
                              size="small"
                              label={`${filter.column} ${filter.operator} ${filter.value}`}
                              onDelete={() => {
                                setFilters((current) =>
                                  current.filter((_, filterIndex) => filterIndex !== index)
                                );
                                setPaginationModel((current) => ({ ...current, page: 0 }));
                              }}
                            />
                          ))
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            No filters applied
                          </Typography>
                        )}
                      </Stack>
                    </Stack>
                  )}

                  {inspectorTab === 'summary' && (
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={700}>
                          Summary
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Run aggregate formulas on numeric columns.
                        </Typography>
                      </Box>

                      <FormControl fullWidth size="small">
                        <InputLabel id="aggregate-column-label">Column</InputLabel>
                        <Select
                          labelId="aggregate-column-label"
                          label="Column"
                          value={aggregateDraft.column}
                          onChange={(event) =>
                            setAggregateDraft((current) => ({
                              ...current,
                              column: event.target.value,
                            }))
                          }
                        >
                          {numericColumns.map((column) => (
                            <MenuItem key={column.name} value={column.name}>
                              {column.name}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>

                      <Stack direction="row" spacing={1}>
                        <FormControl size="small" sx={{ width: 132 }}>
                          <InputLabel id="aggregate-operation-label">Operation</InputLabel>
                          <Select
                            labelId="aggregate-operation-label"
                            label="Operation"
                            value={aggregateDraft.operation}
                            onChange={(event) =>
                              setAggregateDraft((current) => ({
                                ...current,
                                operation: event.target.value as AggregateRequest['operation'],
                              }))
                            }
                          >
                            {aggregateOperations.map((operation) => (
                              <MenuItem key={operation} value={operation}>
                                {operation}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>

                        <FormControl size="small" sx={{ flex: 1 }}>
                          <InputLabel id="aggregate-group-label">Group</InputLabel>
                          <Select
                            labelId="aggregate-group-label"
                            label="Group"
                            value={aggregateDraft.group_by?.[0] || ''}
                            onChange={(event) =>
                              setAggregateDraft((current) => ({
                                ...current,
                                group_by: event.target.value ? [event.target.value] : undefined,
                              }))
                            }
                          >
                            <MenuItem value="">None</MenuItem>
                            {schemaColumns.map((column) => (
                              <MenuItem key={column.name} value={column.name}>
                                {column.name}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Stack>

                      <Button
                        variant="outlined"
                        startIcon={<Calculate />}
                        onClick={runAggregation}
                        disabled={!numericColumns.length || aggregateMutation.isPending}
                      >
                        {aggregateMutation.isPending ? 'Running...' : 'Run'}
                      </Button>

                      {aggregateResult && (
                        <Box
                          sx={{
                            p: 1.5,
                            border: 1,
                            borderColor: 'divider',
                            borderRadius: 1,
                            bgcolor: 'background.default',
                          }}
                        >
                          {aggregateResult.group_results ? (
                            <Stack spacing={1}>
                              {aggregateResult.group_results.slice(0, 6).map((row, index) => (
                                <Typography key={index} variant="body2">
                                  {Object.entries(row)
                                    .map(([key, value]) => `${key}: ${value}`)
                                    .join(' · ')}
                                </Typography>
                              ))}
                            </Stack>
                          ) : (
                            <Typography variant="h5" fontWeight={700}>
                              {aggregateResult.result}
                            </Typography>
                          )}
                        </Box>
                      )}
                    </Stack>
                  )}

                  {inspectorTab === 'fields' && (
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={700}>
                          Fields
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {schemaColumns.length} inferred columns from the dataset.
                        </Typography>
                      </Box>

                      <TextField
                        size="small"
                        label="Search fields"
                        value={fieldSearch}
                        onChange={(event) => setFieldSearch(event.target.value)}
                      />

                      <Divider />

                      <List dense disablePadding>
                        {filteredSchemaColumns.map((column) => (
                          <ListItem
                            key={column.name}
                            disableGutters
                            secondaryAction={
                              <Chip size="small" label={column.semantic_type} />
                            }
                          >
                            <ListItemText
                              primary={column.name}
                              secondary={column.type}
                              primaryTypographyProps={{
                                variant: 'body2',
                                noWrap: true,
                                sx: { fontWeight: 700 },
                              }}
                              secondaryTypographyProps={{ variant: 'caption' }}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Stack>
                  )}

                  {inspectorTab === 'comments' && (
                    <Stack spacing={1.5}>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={700}>
                          Comments
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Attach review notes to the selected cell.
                        </Typography>
                      </Box>

                      {selectedCell && (
                        <Chip
                          size="small"
                          color="warning"
                          variant="outlined"
                          label={`Selected ${selectedCell.column} row ${selectedCell.rowIndex + 1}`}
                        />
                      )}
                      {cursorActivity ? (
                        <Typography variant="body2" color="text.secondary">
                          {cursorActivity.username} is on row {cursorActivity.row}, column{' '}
                          {cursorActivity.column}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          No recent cursor activity
                        </Typography>
                      )}
                      <TextField
                        size="small"
                        label="Comment"
                        value={commentDraft}
                        onChange={(event) => setCommentDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') {
                            event.preventDefault();
                            sendComment();
                          }
                        }}
                      />
                      <Button
                        variant="outlined"
                        startIcon={<Send />}
                        disabled={!canEdit || !commentDraft.trim() || createCommentMutation.isPending}
                        onClick={sendComment}
                      >
                        {createCommentMutation.isPending ? 'Sending...' : 'Send'}
                      </Button>
                      <Stack spacing={1}>
                        {displayedComments.map((comment, index) => (
                          <Box
                            key={`${comment.id || comment.timestamp}-${index}`}
                            sx={{
                              p: 1,
                              border: 1,
                              borderColor: 'divider',
                              borderRadius: 1,
                              bgcolor: 'background.default',
                            }}
                          >
                            <Typography variant="caption" color="text.secondary">
                              {comment.username}
                              {comment.row_index !== null &&
                              comment.row_index !== undefined &&
                              comment.column
                                ? ` · ${comment.column} row ${comment.row_index + 1}`
                                : ' · sheet'}
                            </Typography>
                            <Typography variant="body2">{comment.text}</Typography>
                          </Box>
                        ))}
                      </Stack>
                    </Stack>
                  )}

                  {inspectorTab === 'charts' && (
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={700}>
                          Charts
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Turn selected fields into reusable visuals.
                        </Typography>
                      </Box>

                      <TextField
                        size="small"
                        label="Name"
                        value={chartDraft.name}
                        onChange={(event) =>
                          setChartDraft((current) => ({
                            ...current,
                            name: event.target.value,
                          }))
                        }
                      />
                      <Stack direction="row" spacing={1}>
                        <FormControl size="small" sx={{ width: 128 }}>
                          <InputLabel id="chart-type-label">Type</InputLabel>
                          <Select
                            labelId="chart-type-label"
                            label="Type"
                            value={chartDraft.chart_type}
                            onChange={(event) =>
                              setChartDraft((current) => ({
                                ...current,
                                chart_type: event.target.value as ChartCreate['chart_type'],
                              }))
                            }
                          >
                            {chartTypes.map((type) => (
                              <MenuItem key={type} value={type}>
                                {type}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                        <FormControl size="small" sx={{ flex: 1 }}>
                          <InputLabel id="chart-x-label">X field</InputLabel>
                          <Select
                            labelId="chart-x-label"
                            label="X field"
                            value={String(chartDraft.config.x_axis || '')}
                            onChange={(event) =>
                              setChartDraft((current) => ({
                                ...current,
                                config: {
                                  ...current.config,
                                  x_axis: event.target.value,
                                  labels: event.target.value,
                                },
                              }))
                            }
                          >
                            {schemaColumns.map((column) => (
                              <MenuItem key={column.name} value={column.name}>
                                {column.name}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Stack>
                      <FormControl fullWidth size="small">
                        <InputLabel id="chart-y-label">Y field</InputLabel>
                        <Select
                          labelId="chart-y-label"
                          label="Y field"
                          value={String(chartDraft.config.y_axis || '')}
                          onChange={(event) =>
                            setChartDraft((current) => ({
                              ...current,
                              config: {
                                ...current.config,
                                y_axis: event.target.value,
                                values: event.target.value,
                              },
                            }))
                          }
                        >
                          {numericColumns.map((column) => (
                            <MenuItem key={column.name} value={column.name}>
                              {column.name}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <Button
                        variant="contained"
                        startIcon={<Save />}
                        onClick={saveChart}
                        disabled={!canEdit || !numericColumns.length || createChartMutation.isPending}
                      >
                        {createChartMutation.isPending ? 'Saving...' : 'Save Chart'}
                      </Button>

                      {previewChart && rows.length > 0 && (
                        <Box>
                          <Typography variant="subtitle2" gutterBottom>
                            Preview
                          </Typography>
                          <Box
                            sx={{
                              height: 220,
                              border: 1,
                              borderColor: 'divider',
                              borderRadius: 1,
                              p: 1,
                            }}
                          >
                            <ChartPreview chart={previewChart} rows={rows} />
                          </Box>
                        </Box>
                      )}

                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Saved
                        </Typography>
                        {charts.length ? (
                          <Stack spacing={1.5}>
                            {charts.map((chart) => (
                              <SavedChartCard key={chart.id} chart={chart} fallbackRows={rows} />
                            ))}
                          </Stack>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            No saved charts
                          </Typography>
                        )}
                      </Box>
                    </Stack>
                  )}

                  {inspectorTab === 'access' && (
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={700}>
                          Access
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Current role: {currentRole}
                        </Typography>
                      </Box>

                      {canManageShares ? (
                        <Stack spacing={1}>
                          <TextField
                            size="small"
                            label="Username or email"
                            value={shareTarget}
                            onChange={(event) => setShareTarget(event.target.value)}
                          />
                          <Stack direction="row" spacing={1}>
                            <FormControl size="small" sx={{ width: 128 }}>
                              <InputLabel id="share-role-label">Role</InputLabel>
                              <Select
                                labelId="share-role-label"
                                label="Role"
                                value={shareRole}
                                onChange={(event) =>
                                  setShareRole(event.target.value as 'editor' | 'viewer')
                                }
                              >
                                <MenuItem value="viewer">viewer</MenuItem>
                                <MenuItem value="editor">editor</MenuItem>
                              </Select>
                            </FormControl>
                            <Button
                              variant="contained"
                              disabled={!shareTarget.trim() || createShareMutation.isPending}
                              onClick={() => createShareMutation.mutate()}
                            >
                              Grant
                            </Button>
                          </Stack>
                        </Stack>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Only owners can view and manage collaborator details.
                        </Typography>
                      )}

                      <Divider />
                      {canManageShares && (
                        <List dense disablePadding>
                          {shares.map((share) => (
                            <ListItem
                              key={`${share.role}-${share.user_id}-${share.id}`}
                              disableGutters
                              secondaryAction={
                                share.role !== 'owner' ? (
                                  <Button
                                    size="small"
                                    color="error"
                                    disabled={deleteShareMutation.isPending}
                                    onClick={() => deleteShareMutation.mutate(share)}
                                  >
                                    Remove
                                  </Button>
                                ) : (
                                  <Chip size="small" label={share.role} />
                                )
                              }
                            >
                              <ListItemText
                                primary={share.username}
                                secondary={share.email}
                                primaryTypographyProps={{
                                  variant: 'body2',
                                  sx: { fontWeight: 700 },
                                }}
                                secondaryTypographyProps={{ variant: 'caption' }}
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Stack>
                  )}
                </Box>
              </Paper>
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
}

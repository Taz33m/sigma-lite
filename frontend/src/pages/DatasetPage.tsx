import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Paper,
  IconButton,
  CircularProgress,
  Alert,
  Stack,
  Chip,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import { ArrowBack, Addchart, Description } from '@mui/icons-material';
import { DataGrid } from '@mui/x-data-grid';
import { datasetAPI, sheetAPI } from '@/lib/api';
import {
  buildDatasetGridColumns,
  buildDatasetGridRows,
} from '@/lib/datasetGrid';

export default function DatasetPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const datasetId = Number(id);

  const { data: dataset, isLoading: isDatasetLoading, isError: isDatasetError } = useQuery({
    queryKey: ['dataset', id],
    queryFn: () => datasetAPI.get(datasetId),
    enabled: Number.isFinite(datasetId),
  });

  const { data: datasetData, isLoading: isDataLoading, isError: isDataError } = useQuery({
    queryKey: ['dataset-data', id],
    queryFn: () => datasetAPI.getData(datasetId, 1, 100),
    enabled: Number.isFinite(datasetId),
  });

  const createSheetMutation = useMutation({
    mutationFn: () =>
      sheetAPI.create({
        name: `${dataset?.name || 'Dataset'} Sheet`,
        description: dataset?.description,
        dataset_id: datasetId,
        config: {},
      }),
    onSuccess: (sheet) => {
      toast.success('Sheet created');
      navigate(`/sheet/${sheet.id}`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Could not create sheet');
    },
  });

  const columns = buildDatasetGridColumns(datasetData?.data);
  const rows = buildDatasetGridRows(datasetData?.data);
  const isLoading = isDatasetLoading || isDataLoading;
  const isError = isDatasetError || isDataError || !Number.isFinite(datasetId);

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
          <IconButton edge="start" color="inherit" onClick={() => navigate('/')} sx={{ mr: 1.5 }}>
            <ArrowBack />
          </IconButton>
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Typography variant="subtitle1" fontWeight={700} noWrap>
              {dataset?.name}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap component="div">
              {dataset?.description || dataset?.file_name}
            </Typography>
          </Box>
          <Button
            variant="outlined"
            startIcon={<Addchart />}
            disabled={!dataset || createSheetMutation.isPending}
            onClick={() => createSheetMutation.mutate()}
            size="small"
          >
            {createSheetMutation.isPending ? 'Creating...' : 'Create Sheet'}
          </Button>
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
          <Alert severity="error">Unable to load this dataset.</Alert>
        ) : (
          <>
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
                <Chip size="small" label={`${dataset?.row_count.toLocaleString()} rows`} />
                <Chip size="small" label={`${dataset?.column_count} columns`} />
                <Chip size="small" label={dataset?.file_name || 'CSV'} icon={<Description />} />
              </Stack>
            </Paper>

            <Box
              sx={{
                flex: 1,
                minHeight: { xs: 'auto', lg: 0 },
                display: 'flex',
                gap: 1.5,
                flexDirection: { xs: 'column', lg: 'row' },
              }}
            >
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
                  pageSizeOptions={[10, 25, 50, 100]}
                  getRowId={(row) => row.__row_id}
                  initialState={{
                    pagination: { paginationModel: { pageSize: 25 } },
                  }}
                  checkboxSelection
                  disableRowSelectionOnClick
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
                />
              </Paper>

              <Paper
                variant="outlined"
                sx={{
                  width: { xs: '100%', lg: 360 },
                  height: { xs: 460, lg: '100%' },
                  flexShrink: 0,
                  minHeight: 0,
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column',
                  borderRadius: 1,
                  boxShadow: 'none',
                }}
              >
                <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
                  <Typography variant="subtitle1" fontWeight={700}>
                    Schema
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {dataset?.schema?.columns.length || 0} inferred columns
                  </Typography>
                </Box>
                <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', px: 2 }}>
                  <List dense disablePadding>
                    {dataset?.schema?.columns.map((column) => (
                      <ListItem
                        key={column.name}
                        disableGutters
                        sx={{ py: 1.25, borderBottom: 1, borderColor: 'divider' }}
                      >
                        <ListItemText
                          primary={column.name}
                          secondary={`${column.semantic_type} · ${column.type}`}
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
                </Box>
              </Paper>
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
}

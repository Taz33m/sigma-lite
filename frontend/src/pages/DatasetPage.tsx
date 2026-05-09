import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Container,
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
    <Box>
      <AppBar position="static">
        <Toolbar>
          <IconButton edge="start" color="inherit" onClick={() => navigate('/')} sx={{ mr: 2 }}>
            <ArrowBack />
          </IconButton>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6">{dataset?.name}</Typography>
            <Typography variant="caption">{dataset?.description}</Typography>
          </Box>
          <Button
            color="inherit"
            startIcon={<Addchart />}
            disabled={!dataset || createSheetMutation.isPending}
            onClick={() => createSheetMutation.mutate()}
          >
            {createSheetMutation.isPending ? 'Creating...' : 'Create Sheet'}
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4 }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : isError ? (
          <Alert severity="error">Unable to load this dataset.</Alert>
        ) : (
          <Stack spacing={3}>
            <Paper sx={{ p: 2 }}>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                <Chip label={`${dataset?.row_count.toLocaleString()} rows`} />
                <Chip label={`${dataset?.column_count} columns`} />
                <Chip label={dataset?.file_name || 'CSV'} icon={<Description />} />
              </Stack>
            </Paper>

            <Stack direction={{ xs: 'column', lg: 'row' }} spacing={3}>
              <Paper sx={{ height: 620, flex: 1, minWidth: 0 }}>
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
                />
              </Paper>

              <Paper sx={{ p: 2, width: { xs: '100%', lg: 320 } }}>
                <Typography variant="h6" gutterBottom>
                  Schema
                </Typography>
                <Divider />
                <List dense>
                  {dataset?.schema?.columns.map((column) => (
                    <ListItem key={column.name} disableGutters>
                      <ListItemText
                        primary={column.name}
                        secondary={`${column.semantic_type} · ${column.type}`}
                      />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Stack>
          </Stack>
        )}
      </Container>
    </Box>
  );
}

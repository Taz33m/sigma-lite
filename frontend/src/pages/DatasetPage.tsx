import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Container,
  Box,
  Paper,
  IconButton,
} from '@mui/material';
import { ArrowBack, BarChart } from '@mui/icons-material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { datasetAPI } from '@/lib/api';

export default function DatasetPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: dataset } = useQuery({
    queryKey: ['dataset', id],
    queryFn: () => datasetAPI.get(Number(id)),
  });

  const { data: datasetData } = useQuery({
    queryKey: ['dataset-data', id],
    queryFn: () => datasetAPI.getData(Number(id), 1, 100),
  });

  const columns: GridColDef[] =
    datasetData?.data[0]
      ? Object.keys(datasetData.data[0]).map((key) => ({
          field: key,
          headerName: key,
          width: 150,
          editable: false,
        }))
      : [];

  const rows = datasetData?.data.map((row, index) => ({ id: index, ...row })) || [];

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
          <Button color="inherit" startIcon={<BarChart />}>
            Create Chart
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Paper sx={{ height: 600, width: '100%' }}>
          <DataGrid
            rows={rows}
            columns={columns}
            pageSizeOptions={[10, 25, 50, 100]}
            initialState={{
              pagination: { paginationModel: { pageSize: 25 } },
            }}
            checkboxSelection
            disableRowSelectionOnClick
          />
        </Paper>
      </Container>
    </Box>
  );
}

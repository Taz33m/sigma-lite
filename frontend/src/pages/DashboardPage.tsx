import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Container,
  Grid,
  Card,
  CardContent,
  CardActions,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Box,
  CircularProgress,
  Chip,
} from '@mui/material';
import {
  CloudUpload,
  Logout,
  Add,
  Delete,
  Visibility,
  Storage,
} from '@mui/icons-material';
import { datasetAPI, authAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

export default function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const logout = useAuthStore((state) => state.logout);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadData, setUploadData] = useState({
    name: '',
    description: '',
    file: null as File | null,
  });

  const { data: datasets, isLoading } = useQuery({
    queryKey: ['datasets'],
    queryFn: datasetAPI.list,
  });

  const uploadMutation = useMutation({
    mutationFn: ({ name, file, description }: { name: string; file: File; description?: string }) =>
      datasetAPI.upload(name, file, description),
    onSuccess: () => {
      toast.success('Dataset uploaded successfully!');
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      setShowUpload(false);
      setUploadData({ name: '', description: '', file: null });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Upload failed');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: datasetAPI.delete,
    onSuccess: () => {
      toast.success('Dataset deleted');
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });

  const handleLogout = () => {
    authAPI.logout();
    logout();
    navigate('/login');
  };

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (uploadData.file) {
      uploadMutation.mutate({
        name: uploadData.name,
        file: uploadData.file,
        description: uploadData.description,
      });
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Header */}
      <AppBar position="static">
        <Toolbar>
          <Storage sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            SigmaLite
          </Typography>
          <Button color="inherit" startIcon={<Logout />} onClick={handleLogout}>
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Typography variant="h4" component="h1">
            My Datasets
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setShowUpload(true)}
          >
            Upload Dataset
          </Button>
        </Box>

        {/* Upload Dialog */}
        <Dialog open={showUpload} onClose={() => setShowUpload(false)} maxWidth="sm" fullWidth>
          <form onSubmit={handleUpload}>
            <DialogTitle>Upload Dataset</DialogTitle>
            <DialogContent>
              <TextField
                autoFocus
                margin="dense"
                label="Dataset Name"
                type="text"
                fullWidth
                required
                value={uploadData.name}
                onChange={(e) => setUploadData({ ...uploadData, name: e.target.value })}
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                label="Description (Optional)"
                type="text"
                fullWidth
                multiline
                rows={3}
                value={uploadData.description}
                onChange={(e) => setUploadData({ ...uploadData, description: e.target.value })}
                sx={{ mb: 2 }}
              />
              <Button
                variant="outlined"
                component="label"
                fullWidth
                startIcon={<CloudUpload />}
              >
                {uploadData.file ? uploadData.file.name : 'Choose CSV File'}
                <input
                  type="file"
                  hidden
                  accept=".csv"
                  required
                  onChange={(e) => setUploadData({ ...uploadData, file: e.target.files?.[0] || null })}
                />
              </Button>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setShowUpload(false)}>Cancel</Button>
              <Button type="submit" variant="contained" disabled={uploadMutation.isPending}>
                {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
              </Button>
            </DialogActions>
          </form>
        </Dialog>

        {/* Datasets Grid */}
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : datasets && datasets.length > 0 ? (
          <Grid container spacing={3}>
            {datasets.map((dataset) => (
              <Grid item xs={12} sm={6} md={4} key={dataset.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Storage color="primary" sx={{ mr: 1 }} />
                      <Typography variant="h6" component="div">
                        {dataset.name}
                      </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {dataset.file_name}
                    </Typography>
                    {dataset.description && (
                      <Typography variant="body2" sx={{ mb: 2 }}>
                        {dataset.description}
                      </Typography>
                    )}
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Chip label={`${dataset.row_count.toLocaleString()} rows`} size="small" />
                      <Chip label={`${dataset.column_count} columns`} size="small" />
                    </Box>
                  </CardContent>
                  <CardActions>
                    <Button
                      size="small"
                      startIcon={<Visibility />}
                      onClick={() => navigate(`/dataset/${dataset.id}`)}
                    >
                      View
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      startIcon={<Delete />}
                      onClick={() => deleteMutation.mutate(dataset.id)}
                    >
                      Delete
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        ) : (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <CloudUpload sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              No datasets yet
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Upload your first CSV file to get started
            </Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setShowUpload(true)}
            >
              Upload Dataset
            </Button>
          </Box>
        )}
      </Container>
    </Box>
  );
}

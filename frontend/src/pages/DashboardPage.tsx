import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { datasetAPI, authAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Database, Upload, LogOut, Plus, Trash2, Eye } from 'lucide-react';

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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Database className="w-8 h-8 text-primary-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">SigmaLite</h1>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center px-4 py-2 text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition"
            >
              <LogOut className="w-5 h-5 mr-2" />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-3xl font-bold text-gray-900">My Datasets</h2>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
          >
            <Plus className="w-5 h-5 mr-2" />
            Upload Dataset
          </button>
        </div>

        {/* Upload Modal */}
        {showUpload && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h3 className="text-xl font-bold mb-4">Upload Dataset</h3>
              <form onSubmit={handleUpload} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Dataset Name
                  </label>
                  <input
                    type="text"
                    required
                    value={uploadData.name}
                    onChange={(e) => setUploadData({ ...uploadData, name: e.target.value })}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description (Optional)
                  </label>
                  <textarea
                    value={uploadData.description}
                    onChange={(e) => setUploadData({ ...uploadData, description: e.target.value })}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                    rows={3}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    CSV File
                  </label>
                  <input
                    type="file"
                    accept=".csv"
                    required
                    onChange={(e) => setUploadData({ ...uploadData, file: e.target.files?.[0] || null })}
                    className="w-full px-4 py-2 border rounded-lg"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={uploadMutation.isPending}
                    className="flex-1 bg-primary-600 text-white py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowUpload(false)}
                    className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Datasets Grid */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : datasets && datasets.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {datasets.map((dataset) => (
              <div key={dataset.id} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center">
                    <Database className="w-8 h-8 text-primary-600 mr-3" />
                    <div>
                      <h3 className="font-semibold text-lg text-gray-900">{dataset.name}</h3>
                      <p className="text-sm text-gray-500">{dataset.file_name}</p>
                    </div>
                  </div>
                </div>
                {dataset.description && (
                  <p className="text-gray-600 text-sm mb-4">{dataset.description}</p>
                )}
                <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                  <span>{dataset.row_count.toLocaleString()} rows</span>
                  <span>{dataset.column_count} columns</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => navigate(`/dataset/${dataset.id}`)}
                    className="flex-1 flex items-center justify-center px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    View
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(dataset.id)}
                    className="px-3 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No datasets yet</h3>
            <p className="text-gray-500 mb-4">Upload your first CSV file to get started</p>
            <button
              onClick={() => setShowUpload(true)}
              className="inline-flex items-center px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
            >
              <Plus className="w-5 h-5 mr-2" />
              Upload Dataset
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

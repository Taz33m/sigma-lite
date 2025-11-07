import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { datasetAPI } from '@/lib/api';
import { ArrowLeft, BarChart3 } from 'lucide-react';

export default function DatasetPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: dataset } = useQuery({
    queryKey: ['dataset', id],
    queryFn: () => datasetAPI.get(Number(id)),
  });

  const { data: datasetData } = useQuery({
    queryKey: ['dataset-data', id],
    queryFn: () => datasetAPI.getData(Number(id), 1, 50),
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={() => navigate('/')}
                className="mr-4 p-2 hover:bg-gray-100 rounded-lg transition"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{dataset?.name}</h1>
                <p className="text-sm text-gray-500">{dataset?.description}</p>
              </div>
            </div>
            <button className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition">
              <BarChart3 className="w-5 h-5 mr-2" />
              Create Chart
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {datasetData?.data[0] && Object.keys(datasetData.data[0]).map((key) => (
                  <th key={key} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {key}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {datasetData?.data.map((row, idx) => (
                <tr key={idx}>
                  {Object.values(row).map((value: any, i) => (
                    <td key={i} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {value?.toString() || '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

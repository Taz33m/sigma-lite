import { type MutableRefObject, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Box, Stack, Typography } from '@mui/material';
import { FileDownload } from '@mui/icons-material';
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import type { ChartData } from 'chart.js';
import { Bar, Line, Pie, Scatter } from 'react-chartjs-2';
import type { Chart as SavedChart } from '@/types';
import { sheetAPI } from '@/lib/api';

ChartJS.register(
  ArcElement,
  BarElement,
  CategoryScale,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip
);

function buildChartDataset(chart: SavedChart, rows: Record<string, unknown>[]) {
  const config = chart.config || {};
  const xField = config.x_axis || config.labels || '';
  const yField = Array.isArray(config.y_axis)
    ? config.y_axis[0]
    : config.y_axis || config.values || '';
  const labels = rows.map((row) => String(row[xField] ?? ''));
  const values = rows.map((row) => Number(row[yField] ?? 0));

  if (chart.chart_type === 'scatter') {
    return {
      datasets: [
        {
          label: chart.name,
          data: rows.map((row) => ({
            x: Number(row[xField] ?? 0),
            y: Number(row[yField] ?? 0),
          })),
          backgroundColor: '#1976d2',
        },
      ],
    };
  }

  return {
    labels,
    datasets: [
      {
        label: yField || chart.name,
        data: values,
        backgroundColor:
          chart.chart_type === 'pie'
            ? ['#1976d2', '#dc004e', '#2e7d32', '#ed6c02', '#6d4c41', '#0288d1']
            : '#1976d2',
        borderColor: '#1976d2',
      },
    ],
  };
}

export function ChartPreview({
  chart,
  rows,
  chartRef,
}: {
  chart: SavedChart;
  rows: Record<string, unknown>[];
  chartRef?: MutableRefObject<ChartJS | null>;
}) {
  const data = buildChartDataset(chart, rows);
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
    },
  };

  if (chart.chart_type === 'line') {
    return (
      <Line
        ref={chartRef as any}
        data={data as ChartData<'line', number[], string>}
        options={options}
      />
    );
  }
  if (chart.chart_type === 'scatter') {
    return (
      <Scatter
        ref={chartRef as any}
        data={data as ChartData<'scatter', { x: number; y: number }[], string>}
        options={options}
      />
    );
  }
  if (chart.chart_type === 'pie') {
    return (
      <Pie
        ref={chartRef as any}
        data={data as ChartData<'pie', number[], string>}
        options={options}
      />
    );
  }
  return (
    <Bar
      ref={chartRef as any}
      data={data as ChartData<'bar', number[], string>}
      options={options}
    />
  );
}

export function SavedChartCard({
  chart,
  fallbackRows,
}: {
  chart: SavedChart;
  fallbackRows: Record<string, unknown>[];
}) {
  const chartRef = useRef<ChartJS | null>(null);
  const queryScope = chart.config.query || {
    filters: [],
    logic: 'and' as const,
    sort: null,
    page_size: 1000,
  };
  const { data: chartData, isLoading } = useQuery({
    queryKey: ['chart-data', chart.id, queryScope],
    queryFn: () =>
      sheetAPI.query(chart.sheet_id, {
        filters: queryScope.filters || [],
        logic: queryScope.logic || 'and',
        sort: queryScope.sort || null,
        page: 1,
        page_size: queryScope.page_size || 1000,
      }),
    enabled: chart.id > 0,
  });
  const rows = chartData?.data || fallbackRows;
  const truncated = Boolean(chartData && chartData.total_rows > rows.length);

  const downloadPng = () => {
    const imageUrl = chartRef.current?.toBase64Image();
    if (!imageUrl) {
      return;
    }

    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `${chart.name || 'chart'}.png`;
    link.click();
  };

  return (
    <Box
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        p: 2,
      }}
    >
      <Stack direction="row" justifyContent="space-between" spacing={2}>
        <Typography variant="subtitle1" gutterBottom>
          {chart.name}
        </Typography>
        <Button size="small" startIcon={<FileDownload />} onClick={downloadPng}>
          PNG
        </Button>
      </Stack>
      <Box sx={{ height: 240 }}>
        {isLoading ? (
          <Typography variant="body2" color="text.secondary">
            Loading chart data...
          </Typography>
        ) : (
          <ChartPreview chart={chart} rows={rows} chartRef={chartRef} />
        )}
      </Box>
      {truncated && (
        <Typography variant="caption" color="text.secondary">
          Showing first {rows.length.toLocaleString()} rows
        </Typography>
      )}
    </Box>
  );
}

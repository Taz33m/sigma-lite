import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { useAuthStore } from '@/store/authStore';

// Pages
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import DashboardPage from '@/pages/DashboardPage';
import DatasetPage from '@/pages/DatasetPage';
import SheetPage from '@/pages/SheetPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const authDisabled = import.meta.env.VITE_DISABLE_AUTH === 'true';
  
  // If auth is disabled, allow access
  if (authDisabled) {
    return <>{children}</>;
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <Router>
          <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/"
                element={
                  <PrivateRoute>
                    <DashboardPage />
                  </PrivateRoute>
                }
              />
              <Route
                path="/dataset/:id"
                element={
                  <PrivateRoute>
                    <DatasetPage />
                  </PrivateRoute>
                }
              />
              <Route
                path="/sheet/:id"
                element={
                  <PrivateRoute>
                    <SheetPage />
                  </PrivateRoute>
                }
              />
          </Routes>
          <Toaster position="top-right" />
        </Router>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;

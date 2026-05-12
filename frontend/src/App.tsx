import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider, createTheme, CssBaseline, Box, CircularProgress } from '@mui/material';
import { useAuthStore } from '@/store/authStore';
import { authAPI } from '@/lib/api';

const LoginPage = lazy(() => import('@/pages/LoginPage'));
const RegisterPage = lazy(() => import('@/pages/RegisterPage'));
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const DatasetPage = lazy(() => import('@/pages/DatasetPage'));
const SheetPage = lazy(() => import('@/pages/SheetPage'));

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
  const authReady = useAuthStore((state) => state.authReady);
  
  if (!authReady) {
    return <PageFallback />;
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

function PageFallback() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
      <CircularProgress />
    </Box>
  );
}

function App() {
  const setUser = useAuthStore((state) => state.setUser);
  const logout = useAuthStore((state) => state.logout);
  const setAuthReady = useAuthStore((state) => state.setAuthReady);

  useEffect(() => {
    let cancelled = false;
    const bootstrapAuth = async () => {
      const authDisabled = import.meta.env.VITE_DISABLE_AUTH === 'true';
      const accessToken = localStorage.getItem('access_token');
      if (!authDisabled && !accessToken) {
        setUser(null);
        setAuthReady(true);
        return;
      }

      try {
        const user = await authAPI.me();
        if (!cancelled) {
          setUser(user);
        }
      } catch {
        if (!cancelled) {
          logout();
        }
      } finally {
        if (!cancelled) {
          setAuthReady(true);
        }
      }
    };

    bootstrapAuth();
    return () => {
      cancelled = true;
    };
  }, [logout, setAuthReady, setUser]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Suspense fallback={<PageFallback />}>
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
          </Suspense>
          <Toaster position="top-right" />
        </Router>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;

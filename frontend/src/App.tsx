import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuth } from './hooks/useAuth';
import Layout from './components/layout/Layout';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import MessagesPage from './pages/MessagesPage';
import AdminPage from './pages/AdminPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  const { isAuthenticated, fetchCurrentUser } = useAuth();

  useEffect(() => {
    if (isAuthenticated) fetchCurrentUser();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <RequireAuth>
                <Layout>
                  <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/messages" element={<MessagesPage />} />
                    <Route path="/admin" element={<AdminPage />} />
                    {/* Placeholder routes for remaining pages */}
                    <Route path="/forums" element={<PlaceholderPage title="Forums" />} />
                    <Route path="/resources" element={<PlaceholderPage title="Resources" />} />
                    <Route path="/news" element={<PlaceholderPage title="News" />} />
                    <Route path="/news/:id" element={<PlaceholderPage title="News Article" />} />
                    <Route path="/surveys" element={<PlaceholderPage title="Surveys" />} />
                    <Route path="/profile" element={<PlaceholderPage title="My Profile" />} />
                  </Routes>
                </Layout>
              </RequireAuth>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <div className="w-16 h-16 rounded-2xl bg-gradient-brand-soft flex items-center justify-center shadow-brand mb-5">
        <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
        </svg>
      </div>
      <h1 className="text-2xl font-extrabold text-navy-DEFAULT mb-2">{title}</h1>
      <p className="text-sm text-navy-DEFAULT/50 max-w-xs text-center">
        This section is connected to the API and ready for further development.
      </p>
    </div>
  );
}

export default App;

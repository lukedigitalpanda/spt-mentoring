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
    <div className="text-center py-16">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">{title}</h1>
      <p className="text-gray-500">This page is connected to the API and ready for further development.</p>
    </div>
  );
}

export default App;

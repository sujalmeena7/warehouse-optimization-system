import { useEffect, useMemo, useState } from "react";
import "@/App.css";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster, toast } from "@/components/ui/sonner";
import { AppShell } from "@/components/layout/AppShell";
import { AuthProvider, AuthContext } from "@/context/AuthContext";
import { useAuth } from "@/hooks/useAuth";
import { LoginPage } from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import DashboardPage from "@/pages/DashboardPage";
import InventoryPage from "@/pages/InventoryPage";
import OrdersPage from "@/pages/OrdersPage";
import RoutesPage from "@/pages/RoutesPage";
import WarehouseLayoutPage from "@/pages/WarehouseLayoutPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import AlertsPage from "@/pages/AlertsPage";
import AdminUsersPage from "@/pages/AdminUsersPage";
import ImportPage from "@/pages/ImportPage";
import SearchPage from "@/pages/SearchPage";
import NotificationCenter from "@/pages/NotificationCenter";
import ForecastingDashboard from "@/pages/ForecastingDashboard";
import AnalyticsDashboard from "@/pages/AnalyticsDashboard";
import { warehouseApi } from "@/lib/api";
import { canAccessPage } from "@/lib/permissions";

const ProtectedLayout = () => {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return (
    <AppShell user={user}>
      <Outlet />
    </AppShell>
  );
};

const PageGuard = ({ page, children }) => {
  const { user } = useAuth();
  if (!user || !canAccessPage(user, page)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
};

const AdminGuard = ({ children }) => {
  const { user } = useAuth();
  if (!user || user.role !== "Admin") {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
};

function AppContent() {
  const { user, accessToken, loading } = useAuth();
  const [errors, setErrors] = useState([]);

  console.log('[AppContent] Loading:', loading, 'User:', user?.email, 'Token:', accessToken ? 'YES' : 'NO');

  useEffect(() => {
    const handleError = (event) => {
      console.error('[ERROR EVENT]', event.error);
      setErrors(prev => [...prev, event.error?.message || String(event)].slice(-5));
    };
    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, []);

  useEffect(() => {
    if (!accessToken || !user) return;
  }, [accessToken, user]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900"></div>
          <p className="text-sm text-slate-600">Loading warehouse system...</p>
        </div>
      </div>
    );
  }

  if (errors.length > 0) {
    return (
      <div className="flex h-screen items-center justify-center bg-red-50">
        <div className="max-w-md p-4 bg-white border border-red-200 rounded">
          <h2 className="text-red-800 font-bold">Application Error</h2>
          {errors.map((err, i) => (
            <p key={i} className="text-sm text-red-700 mt-2">{err}</p>
          ))}
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route path="/" element={<ProtectedLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route
          path="dashboard"
          element={
            <PageGuard page="dashboard">
              <DashboardPage />
            </PageGuard>
          }
        />
        <Route
          path="inventory"
          element={
            <PageGuard page="inventory">
              <InventoryPage />
            </PageGuard>
          }
        />
        <Route
          path="orders"
          element={
            <PageGuard page="orders">
              <OrdersPage />
            </PageGuard>
          }
        />
        <Route
          path="routes"
          element={
            <PageGuard page="routes">
              <RoutesPage />
            </PageGuard>
          }
        />
        <Route
          path="layout-optimization"
          element={
            <PageGuard page="layout">
              <WarehouseLayoutPage />
            </PageGuard>
          }
        />
        <Route
          path="analytics"
          element={
            <PageGuard page="analytics">
              <AnalyticsPage />
            </PageGuard>
          }
        />
        <Route
          path="analytics/advanced"
          element={
            <PageGuard page="analytics">
              <AnalyticsDashboard />
            </PageGuard>
          }
        />
        <Route
          path="forecasting"
          element={
            <PageGuard page="analytics">
              <ForecastingDashboard />
            </PageGuard>
          }
        />
        <Route
          path="alerts"
          element={
            <PageGuard page="alerts">
              <AlertsPage />
            </PageGuard>
          }
        />
        <Route
          path="admin/users"
          element={
            <AdminGuard>
              <AdminUsersPage />
            </AdminGuard>
          }
        />
        <Route
          path="import"
          element={
            <PageGuard page="inventory">
              <ImportPage />
            </PageGuard>
          }
        />
        <Route
          path="search"
          element={
            <PageGuard page="inventory">
              <SearchPage />
            </PageGuard>
          }
        />
        <Route
          path="notifications"
          element={
            <PageGuard page="dashboard">
              <NotificationCenter />
            </PageGuard>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <BrowserRouter>
        <AuthProvider>
          <AppContent />
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;

import { useEffect, useMemo, useState } from "react";
import "@/App.css";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster, toast } from "@/components/ui/sonner";
import { AppShell } from "@/components/layout/AppShell";
import { LoginPage } from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import InventoryPage from "@/pages/InventoryPage";
import OrdersPage from "@/pages/OrdersPage";
import RoutesPage from "@/pages/RoutesPage";
import WarehouseLayoutPage from "@/pages/WarehouseLayoutPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import AlertsPage from "@/pages/AlertsPage";
import { warehouseApi } from "@/lib/api";
import { canAccessPage } from "@/lib/permissions";

const SESSION_KEY = "warehouse-session";

const ProtectedLayout = ({ session, onLogout }) => {
  if (!session) {
    return <Navigate to="/login" replace />;
  }
  return (
    <AppShell user={session} onLogout={onLogout}>
      <Outlet />
    </AppShell>
  );
};

const PageGuard = ({ session, page, children }) => {
  if (!session || !canAccessPage(session, page)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
};

function App() {
  const [session, setSession] = useState(() => {
    const stored = localStorage.getItem(SESSION_KEY);
    return stored ? JSON.parse(stored) : null;
  });

  const userRole = useMemo(() => session?.role, [session]);

  useEffect(() => {
    if (!userRole) return;
    warehouseApi.seedDatabase().catch(() => {
      toast.error("Unable to refresh demo seed data right now.");
    });
  }, [userRole]);

  const handleLogin = async (payload) => {
    const response = await warehouseApi.demoLogin(payload);
    setSession(response);
    localStorage.setItem(SESSION_KEY, JSON.stringify(response));
    toast.success(`Welcome ${response.name}. Control tower is ready.`);
  };

  const handleLogout = () => {
    setSession(null);
    localStorage.removeItem(SESSION_KEY);
    toast.info("You are now signed out.");
  };

  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage onLogin={handleLogin} isAuthenticated={Boolean(session)} />} />

          <Route path="/" element={<ProtectedLayout session={session} onLogout={handleLogout} />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route
              path="dashboard"
              element={
                <PageGuard session={session} page="dashboard">
                  <DashboardPage user={session} />
                </PageGuard>
              }
            />
            <Route
              path="inventory"
              element={
                <PageGuard session={session} page="inventory">
                  <InventoryPage user={session} />
                </PageGuard>
              }
            />
            <Route
              path="orders"
              element={
                <PageGuard session={session} page="orders">
                  <OrdersPage user={session} />
                </PageGuard>
              }
            />
            <Route
              path="routes"
              element={
                <PageGuard session={session} page="routes">
                  <RoutesPage user={session} />
                </PageGuard>
              }
            />
            <Route
              path="layout-optimization"
              element={
                <PageGuard session={session} page="layout">
                  <WarehouseLayoutPage user={session} />
                </PageGuard>
              }
            />
            <Route
              path="analytics"
              element={
                <PageGuard session={session} page="analytics">
                  <AnalyticsPage user={session} />
                </PageGuard>
              }
            />
            <Route
              path="alerts"
              element={
                <PageGuard session={session} page="alerts">
                  <AlertsPage user={session} />
                </PageGuard>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        <Toaster richColors position="top-right" />
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;

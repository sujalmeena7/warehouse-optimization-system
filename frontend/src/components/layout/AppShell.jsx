import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Bell, Boxes, ChartNoAxesCombined, LayoutGrid, LogOut, MapPinned, Menu, PackageSearch, Truck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

const navItems = [
  { key: "dashboard", label: "Dashboard", to: "/dashboard", icon: ChartNoAxesCombined },
  { key: "inventory", label: "Inventory", to: "/inventory", icon: Boxes },
  { key: "orders", label: "Orders", to: "/orders", icon: Truck },
  { key: "routes", label: "Picking Routes", to: "/routes", icon: MapPinned },
  { key: "layout", label: "Layout Optimization", to: "/layout-optimization", icon: LayoutGrid },
  { key: "analytics", label: "Analytics", to: "/analytics", icon: PackageSearch },
  { key: "alerts", label: "Alerts", to: "/alerts", icon: Bell },
];

const SidebarContent = ({ locationPath, allowedPages }) => (
  <div className="flex h-full flex-col gap-6">
    <div className="space-y-2 border-b border-slate-200 pb-6">
      <p className="font-mono text-xs uppercase tracking-[0.24em] text-slate-500" data-testid="sidebar-eyebrow-text">
        Swiss Industrial Utility
      </p>
      <h1 className="font-heading text-2xl font-bold text-slate-900" data-testid="sidebar-title-text">
        Depot Smart
      </h1>
    </div>

    <nav className="space-y-2" data-testid="sidebar-navigation">
      {navItems
        .filter((item) => allowedPages.includes(item.key))
        .map((item) => {
          const Icon = item.icon;
          const active = locationPath === item.to;
          return (
            <Link
              key={item.key}
              to={item.to}
              data-testid={`sidebar-nav-link-${item.key}`}
              className={`flex items-center gap-3 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "border-slate-900 bg-slate-900 text-white"
                  : "border-slate-200 bg-white text-slate-700 hover:bg-slate-100"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
    </nav>
  </div>
);

export const AppShell = ({ user, onLogout, children }) => {
  const location = useLocation();
  const allowedPages = user?.allowed_pages || [];

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900" data-testid="app-shell-root">
      <div className="mx-auto flex max-w-[1600px] gap-6 px-4 py-4 md:px-8 md:py-8">
        <aside className="hidden w-72 rounded-xl border border-slate-200 bg-white p-6 lg:block" data-testid="desktop-sidebar">
          <SidebarContent locationPath={location.pathname} allowedPages={allowedPages} />
        </aside>

        <div className="flex min-h-[90vh] flex-1 flex-col gap-4">
          <header className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-4 md:px-6" data-testid="top-header-bar">
            <div className="flex items-center gap-3">
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="outline" size="icon" className="lg:hidden" data-testid="mobile-nav-trigger-button">
                    <Menu className="h-4 w-4" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="border-slate-200 bg-white">
                  <SidebarContent locationPath={location.pathname} allowedPages={allowedPages} />
                </SheetContent>
              </Sheet>

              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
                <p className="text-sm text-slate-500" data-testid="header-greeting-text">
                  Warehouse Optimization Console
                </p>
                <h2 className="font-heading text-xl font-semibold" data-testid="header-user-text">
                  Welcome back, {user?.name}
                </h2>
              </motion.div>
            </div>

            <div className="flex items-center gap-2">
              <Badge className="rounded-md bg-orange-100 text-orange-700" data-testid="header-role-badge">
                {user?.role}
              </Badge>
              <Button variant="outline" onClick={onLogout} data-testid="logout-button">
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </Button>
            </div>
          </header>

          <main className="flex-1">{children}</main>
        </div>
      </div>
    </div>
  );
};

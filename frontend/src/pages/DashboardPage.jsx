import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Boxes, ClipboardList, Gauge } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { warehouseApi } from "@/lib/api";

export default function DashboardPage({ user }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    warehouseApi.getOverview(user.role).then(setData);
  }, [user.role]);

  if (!data) {
    return <div className="rounded-xl border border-slate-200 bg-white p-6" data-testid="dashboard-loading-state">Loading dashboard...</div>;
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="space-y-6" data-testid="dashboard-page-root">
      <Card className="overflow-hidden border-slate-200">
        <CardContent className="grid gap-6 p-0 md:grid-cols-[1.2fr_1fr]">
          <div className="space-y-3 p-6" data-testid="dashboard-hero-content">
            <p className="font-mono text-xs uppercase tracking-[0.25em] text-slate-500" data-testid="dashboard-hero-tag">
              Real-Time Control
            </p>
            <h1 className="font-heading text-4xl font-bold text-slate-900" data-testid="dashboard-main-heading">
              Warehouse Optimization Command Center
            </h1>
            <p className="text-sm text-slate-600" data-testid="dashboard-subheading-text">
              Track stock health, prioritize orders, and generate optimized pick routes from a single system.
            </p>
          </div>
          <img
            src="https://images.pexels.com/photos/7019311/pexels-photo-7019311.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
            alt="Warehouse operations"
            className="h-56 w-full object-cover md:h-full"
            data-testid="dashboard-hero-image"
          />
        </CardContent>
      </Card>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" data-testid="dashboard-kpi-grid">
        <KpiCard title="Total SKUs" value={data.kpis.total_skus} icon={Boxes} hint="Tracked live inventory units" testId="kpi-total-skus" />
        <KpiCard title="Low Stock" value={data.kpis.low_stock_items} icon={AlertTriangle} hint="Immediate replenishment candidates" testId="kpi-low-stock" />
        <KpiCard title="Open Orders" value={data.kpis.open_orders} icon={ClipboardList} hint="Queue requiring warehouse action" testId="kpi-open-orders" />
        <KpiCard title="Picking Efficiency" value={`${data.kpis.picking_efficiency}%`} icon={Gauge} hint={`${data.kpis.space_utilization}% space utilization`} testId="kpi-picking-efficiency" />
      </section>

      <section className="grid gap-6 xl:grid-cols-2" data-testid="dashboard-main-grid">
        <Card className="border-slate-200" data-testid="dashboard-orders-card">
          <CardHeader>
            <CardTitle className="font-heading text-xl" data-testid="dashboard-recent-orders-title">Recent Orders</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead data-testid="recent-order-reference-header">Reference</TableHead>
                  <TableHead data-testid="recent-order-priority-header">Priority</TableHead>
                  <TableHead data-testid="recent-order-status-header">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.recent_orders.map((order) => (
                  <TableRow key={order.id} data-testid={`recent-order-row-${order.id}`}>
                    <TableCell data-testid={`recent-order-reference-${order.id}`}>{order.reference}</TableCell>
                    <TableCell data-testid={`recent-order-priority-${order.id}`} className="capitalize">{order.priority}</TableCell>
                    <TableCell><StatusBadge status={order.status} testId={`recent-order-status-${order.id}`} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="border-slate-200" data-testid="dashboard-efficiency-chart-card">
          <CardHeader>
            <CardTitle className="font-heading text-xl" data-testid="dashboard-efficiency-chart-title">Picking Efficiency Trend</CardTitle>
          </CardHeader>
          <CardContent className="h-[290px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.efficiency_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                <XAxis dataKey="day" stroke="#475569" />
                <YAxis stroke="#475569" />
                <Tooltip />
                <Line type="monotone" dataKey="avg_pick_minutes" stroke="#F97316" strokeWidth={3} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-2" data-testid="dashboard-alerts-reorder-grid">
        <Card className="border-slate-200" data-testid="dashboard-low-stock-card">
          <CardHeader><CardTitle className="font-heading text-xl" data-testid="low-stock-title">Low Stock Alerts</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {data.low_stock.map((item) => (
              <div className="flex items-center justify-between rounded-lg border border-slate-200 p-3" key={item.id} data-testid={`low-stock-item-${item.id}`}>
                <div>
                  <p className="text-sm font-semibold text-slate-900" data-testid={`low-stock-name-${item.id}`}>{item.name}</p>
                  <p className="text-xs text-slate-500" data-testid={`low-stock-bin-${item.id}`}>{item.bin_code} · Qty {item.quantity}</p>
                </div>
                <StatusBadge status={item.stock_status} testId={`low-stock-status-${item.id}`} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-slate-200" data-testid="dashboard-reorder-card">
          <CardHeader><CardTitle className="font-heading text-xl" data-testid="reorder-title">Suggested Reorders</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {data.reorder_recommendations.map((item) => (
              <div className="rounded-lg border border-slate-200 p-3" key={item.sku} data-testid={`reorder-item-${item.sku}`}>
                <p className="text-sm font-semibold" data-testid={`reorder-name-${item.sku}`}>{item.name}</p>
                <p className="text-xs text-slate-600" data-testid={`reorder-values-${item.sku}`}>
                  Current: {item.current_qty} · Reorder Point: {item.reorder_point} · Suggested: {item.suggested_qty}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </motion.div>
  );
}

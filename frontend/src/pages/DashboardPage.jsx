import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Package,
  Truck,
  AlertTriangle,
  Gauge,
  Boxes,
  Timer,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  RefreshCw,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { warehouseApi } from "@/lib/api";
import "./DashboardPage.css";

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" } },
};

const STATUS_COLORS = {
  healthy: { bg: "#ecfdf5", text: "#059669", dot: "#10b981" },
  low: { bg: "#fffbeb", text: "#d97706", dot: "#f59e0b" },
  critical: { bg: "#fef2f2", text: "#dc2626", dot: "#ef4444" },
};

const ORDER_BADGE = {
  queued: "bg-slate-100 text-slate-600",
  picking: "bg-blue-100 text-blue-700",
  packed: "bg-amber-100 text-amber-700",
  shipped: "bg-emerald-100 text-emerald-700",
};

const CHART_GRADIENT = [
  { offset: "0%", color: "#3b82f6", opacity: 0.35 },
  { offset: "100%", color: "#3b82f6", opacity: 0.02 },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const result = await warehouseApi.getOverview();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    fetchData();
  }, [user]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  if (loading) {
    return (
      <div className="dash-loading">
        <div className="dash-loading-spinner" />
        <p>Loading dashboard…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dash-error">
        <AlertTriangle size={24} />
        <p>{error}</p>
        <Button variant="outline" onClick={handleRefresh}>Retry</Button>
      </div>
    );
  }

  if (!data) return null;

  const { kpis, recent_orders, low_stock, efficiency_trend, reorder_recommendations } = data;

  const kpiCards = [
    {
      label: "Total SKUs",
      value: kpis.total_skus,
      icon: Boxes,
      color: "#3b82f6",
      bg: "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)",
    },
    {
      label: "Low Stock Items",
      value: kpis.low_stock_items,
      icon: AlertTriangle,
      color: "#f59e0b",
      bg: "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)",
      alert: kpis.low_stock_items > 0,
    },
    {
      label: "Open Orders",
      value: kpis.open_orders,
      icon: Truck,
      color: "#8b5cf6",
      bg: "linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%)",
    },
    {
      label: "Space Utilization",
      value: `${kpis.space_utilization}%`,
      icon: Gauge,
      color: "#10b981",
      bg: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)",
    },
    {
      label: "Pick Efficiency",
      value: `${kpis.picking_efficiency}%`,
      icon: Timer,
      color: "#06b6d4",
      bg: "linear-gradient(135deg, #ecfeff 0%, #cffafe 100%)",
    },
  ];

  return (
    <motion.div
      className="dash-root"
      variants={stagger}
      initial="hidden"
      animate="show"
    >
      {/* Header */}
      <motion.div className="dash-header" variants={fadeUp}>
        <div>
          <h1 className="dash-title">Dashboard</h1>
          <p className="dash-subtitle">Real-time warehouse performance overview</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          className="dash-refresh-btn"
        >
          <RefreshCw size={14} className={refreshing ? "spin" : ""} />
          Refresh
        </Button>
      </motion.div>

      {/* KPI Cards */}
      <motion.div className="dash-kpi-grid" variants={stagger}>
        {kpiCards.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <motion.div
              key={kpi.label}
              className={`dash-kpi-card ${kpi.alert ? "alert-pulse" : ""}`}
              style={{ background: kpi.bg }}
              variants={fadeUp}
              whileHover={{ y: -4, boxShadow: "0 8px 25px rgba(0,0,0,0.1)" }}
            >
              <div className="kpi-top">
                <span className="kpi-label">{kpi.label}</span>
                <div className="kpi-icon-wrap" style={{ background: `${kpi.color}18` }}>
                  <Icon size={18} style={{ color: kpi.color }} />
                </div>
              </div>
              <span className="kpi-number" style={{ color: kpi.color }}>
                {kpi.value}
              </span>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Charts Row */}
      <motion.div className="dash-charts-row" variants={stagger}>
        {/* Efficiency Trend */}
        <motion.div variants={fadeUp} className="dash-chart-card">
          <Card className="h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold text-slate-700">
                7-Day Efficiency Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={efficiency_trend} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <defs>
                    <linearGradient id="effGrad" x1="0" y1="0" x2="0" y2="1">
                      {CHART_GRADIENT.map((g) => (
                        <stop key={g.offset} offset={g.offset} stopColor={g.color} stopOpacity={g.opacity} />
                      ))}
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="day" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: "#fff",
                      borderRadius: "8px",
                      border: "1px solid #e2e8f0",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                      fontSize: "13px",
                    }}
                    formatter={(value, name) =>
                      name === "completed_orders"
                        ? [value, "Orders Completed"]
                        : [value + " min", "Avg Pick Time"]
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="completed_orders"
                    stroke="#3b82f6"
                    fill="url(#effGrad)"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: "#fff", stroke: "#3b82f6", strokeWidth: 2 }}
                    activeDot={{ r: 6, fill: "#3b82f6" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="avg_pick_minutes"
                    stroke="#f59e0b"
                    fill="none"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
              <div className="chart-legend">
                <span><span className="legend-dot blue" /> Orders Completed</span>
                <span><span className="legend-dot amber dashed" /> Avg Pick Time (min)</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Reorder Recommendations */}
        <motion.div variants={fadeUp} className="dash-reorder-card">
          <Card className="h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold text-slate-700">
                Reorder Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              {reorder_recommendations && reorder_recommendations.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart
                    data={reorder_recommendations.map((r) => ({
                      name: r.sku,
                      current: r.current_qty,
                      needed: r.suggested_qty,
                    }))}
                    margin={{ top: 5, right: 10, left: -10, bottom: 5 }}
                    barCategoryGap="25%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        background: "#fff",
                        borderRadius: "8px",
                        border: "1px solid #e2e8f0",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                        fontSize: "13px",
                      }}
                    />
                    <Bar dataKey="current" name="Current Stock" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="needed" name="Suggested Reorder" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-state">
                  <Package size={32} className="text-slate-300" />
                  <p>All stock levels healthy</p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Bottom Row */}
      <motion.div className="dash-bottom-row" variants={stagger}>
        {/* Recent Orders */}
        <motion.div variants={fadeUp} className="dash-orders-card">
          <Card className="h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold text-slate-700">
                  Recent Orders
                </CardTitle>
                <Badge variant="outline" className="text-xs font-normal">
                  {recent_orders?.length || 0} orders
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="dash-orders-list">
                {recent_orders?.map((order, idx) => (
                  <div key={order.id || idx} className="dash-order-row">
                    <div className="order-info">
                      <span className="order-ref">{order.reference}</span>
                      <span className="order-dest">{order.destination}</span>
                    </div>
                    <div className="order-meta">
                      <Badge className={`text-xs ${ORDER_BADGE[order.status] || ""}`}>
                        {order.status}
                      </Badge>
                      <span className="order-items">{order.items?.length || 0} items</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Low Stock */}
        <motion.div variants={fadeUp} className="dash-low-stock-card">
          <Card className="h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold text-slate-700">
                  Low Stock Alerts
                </CardTitle>
                <Badge variant="outline" className="text-xs font-normal border-amber-300 text-amber-600">
                  <AlertTriangle size={12} className="mr-1" />
                  {low_stock?.length || 0} items
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="dash-stock-list">
                {low_stock?.map((item, idx) => {
                  const status = STATUS_COLORS[item.stock_status] || STATUS_COLORS.healthy;
                  const pct = Math.round((item.quantity / (item.max_capacity || 100)) * 100);
                  return (
                    <div key={item.id || idx} className="dash-stock-row">
                      <div className="stock-info">
                        <span className="stock-sku">{item.sku}</span>
                        <span className="stock-name">{item.name}</span>
                      </div>
                      <div className="stock-bar-wrap">
                        <div className="stock-bar">
                          <div
                            className="stock-bar-fill"
                            style={{
                              width: `${Math.min(pct, 100)}%`,
                              background: status.dot,
                            }}
                          />
                        </div>
                        <span className="stock-qty" style={{ color: status.text }}>
                          {item.quantity}/{item.max_capacity}
                        </span>
                      </div>
                      <Badge
                        className="text-xs"
                        style={{ background: status.bg, color: status.text, border: "none" }}
                      >
                        {item.stock_status}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

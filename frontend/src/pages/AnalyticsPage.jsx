import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { warehouseApi } from "@/lib/api";

export default function AnalyticsPage({ user }) {
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    warehouseApi.getAnalytics(user.role).then(setAnalytics);
  }, [user.role]);

  if (!analytics) {
    return <div className="rounded-xl border border-slate-200 bg-white p-6" data-testid="analytics-loading-state">Loading analytics...</div>;
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="space-y-6" data-testid="analytics-page-root">
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="font-heading text-2xl" data-testid="analytics-title-text">Warehouse Analytics</CardTitle>
          <p className="text-sm text-slate-500" data-testid="analytics-subtitle-text">Data-backed turnover insights, service levels, and demand forecasts.</p>
        </CardHeader>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="border-slate-200" data-testid="analytics-turnover-card">
          <CardHeader><CardTitle data-testid="analytics-turnover-title">Category Turnover Index</CardTitle></CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics.category_turnover}>
                <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                <XAxis dataKey="category" stroke="#475569" />
                <YAxis stroke="#475569" />
                <Tooltip />
                <Bar dataKey="turnover_index" fill="#0F172A" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-slate-200" data-testid="analytics-fulfillment-card">
          <CardHeader><CardTitle data-testid="analytics-fulfillment-title">Fulfillment SLA Trend</CardTitle></CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics.fulfillment_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                <XAxis dataKey="day" stroke="#475569" />
                <YAxis stroke="#475569" />
                <Tooltip />
                <Line type="monotone" dataKey="on_time_rate" stroke="#F97316" strokeWidth={3} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200" data-testid="analytics-demand-card">
        <CardHeader><CardTitle data-testid="analytics-demand-title">7-Day Demand Forecast</CardTitle></CardHeader>
        <CardContent className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={analytics.demand_forecast}>
              <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
              <XAxis dataKey="day" stroke="#475569" />
              <YAxis stroke="#475569" />
              <Tooltip />
              <Area type="monotone" dataKey="projected_units" fill="#FDBA74" stroke="#EA580C" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </motion.div>
  );
}

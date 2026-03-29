import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Package, Truck, AlertCircle, TrendingUp, DollarSign, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import KPICard from '@/components/analytics/KPICard';
import TrendChart from '@/components/analytics/TrendChart';
import { warehouseApi } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import './AnalyticsDashboard.css';

const AnalyticsDashboard = () => {
  const { user } = useAuth();
  const [kpis, setKpis] = useState(null);
  const [inventory, setInventory] = useState(null);
  const [orders, setOrders] = useState(null);
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState('today');

  useEffect(() => {
    loadData();
  }, [timeRange]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [kpiRes, invRes, ordRes, trendRes] = await Promise.all([
        warehouseApi.get(`/analytics/dashboard?time_range=${timeRange}`),
        warehouseApi.get('/analytics/inventory'),
        warehouseApi.get('/analytics/orders'),
        warehouseApi.get('/analytics/trends'),
      ]);

      setKpis(kpiRes);
      setInventory(invRes);
      setOrders(ordRes);
      setTrends(trendRes);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="analytics-dashboard"
    >
      <div className="dashboard-header">
        <div>
          <h1>Analytics Dashboard</h1>
          <p className="subtitle">Real-time warehouse insights and performance metrics</p>
        </div>
        <div className="time-range-selector">
          {['today', 'week', 'month', 'year'].map(range => (
            <button
              key={range}
              className={`range-btn ${timeRange === range ? 'active' : ''}`}
              onClick={() => setTimeRange(range)}
            >
              {range.charAt(0).toUpperCase() + range.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading analytics...</div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="kpi-grid">
            <KPICard
              title="Orders Today"
              value={kpis?.orders_today || 0}
              icon={Truck}
              color="blue"
            />
            <KPICard
              title="Fulfillment Rate"
              value={kpis?.fulfillment_rate || 0}
              unit="%"
              icon={TrendingUp}
              color="green"
            />
            <KPICard
              title="Inventory Value"
              value={kpis?.inventory_value ? '$' + (kpis.inventory_value / 1000).toFixed(0) + 'K' : '$0'}
              icon={DollarSign}
              color="purple"
            />
            <KPICard
              title="Low Stock Items"
              value={kpis?.low_stock_items || 0}
              icon={AlertCircle}
              color="orange"
            />
            <KPICard
              title="Inventory Turnover"
              value={kpis?.inventory_turnover?.toFixed(1) || 0}
              unit="x/year"
              icon={Zap}
              color="blue"
            />
            <KPICard
              title="Total Items"
              value={kpis?.total_items || 0}
              icon={Package}
              color="green"
            />
          </div>

          {/* Charts */}
          <div className="charts-grid">
            <Card className="chart-card">
              <CardHeader>
                <CardTitle>Performance Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <TrendChart
                  data={trends?.trends}
                  dataKeys={['orders', 'fulfillment_rate']}
                  height={300}
                  type="line"
                />
              </CardContent>
            </Card>
          </div>

          {/* Metrics */}
          <div className="metrics-grid">
            <Card>
              <CardHeader>
                <CardTitle>Orders by Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="status-list">
                  {orders?.by_status?.map(status => (
                    <div key={status.status} className="status-item">
                      <span className={`label status-${status.status}`}>{status.status}</span>
                      <span className="count">{status.count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Orders by Priority</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="priority-list">
                  {orders?.by_priority?.map(priority => (
                    <div key={priority.priority} className="priority-item">
                      <span className={`label priority-${priority.priority}`}>{priority.priority}</span>
                      <span className="count">{priority.count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Inventory by Category</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="category-list">
                  {inventory?.by_category?.slice(0, 5).map(cat => (
                    <div key={cat.category} className="category-item">
                      <span className="label">{cat.category}</span>
                      <span className="value">{cat.items} items</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Summary Stats */}
          <Card className="summary-card">
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="summary-grid">
                <div className="summary-item">
                  <span className="label">Total Orders (Period)</span>
                  <span className="value">{orders?.total_orders || 0}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Total Items Ordered</span>
                  <span className="value">{orders?.total_items_ordered || 0}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Total Inventory Items</span>
                  <span className="value">{inventory?.total_items || 0}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Total Quantity in Stock</span>
                  <span className="value">{inventory?.total_quantity || 0}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Critical Stock Items</span>
                  <span className="value">{kpis?.critical_stock_items || 0}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Overdue Orders</span>
                  <span className="value">{kpis?.overdue_orders || 0}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </motion.div>
  );
};

export default AnalyticsDashboard;

import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { warehouseApi } from '../../lib/api';
import './TrendAnalysis.css';

const TrendAnalysis = ({ sku, days = 90 }) => {
  const [trend, setTrend] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadTrend();
  }, [sku, days]);

  const loadTrend = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await warehouseApi.get(`/forecasting/trends/${sku}?days=${days}`);

      if (response.status === 'success') {
        // Transform history for chart
        const chartData = response.history.map(h => ({
          date: new Date(h.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          quantity: h.quantity,
        }));
        setTrend({ ...response, chartData });
      } else if (response.status === 'insufficient_data') {
        setTrend({ isInsufficient: true });
      } else {
        setError(response.message || 'Failed to load trend');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="trend-analysis loading">Loading trend analysis...</div>;
  }

  if (error) {
    return <div className="trend-analysis error">Error: {error}</div>;
  }

  if (!trend) {
    return <div className="trend-analysis empty">No trend data</div>;
  }

  if (trend.isInsufficient) {
    return (
      <div className="trend-analysis empty">
        <div className="trend-header">
          <h3>Trend Analysis</h3>
        </div>
        <p>Not enough historical data to generate trend analysis (minimum 3 records required).</p>
      </div>
    );
  }

  const trendColor = trend.trend === 'increasing' ? '#00aa44' : (trend.trend === 'decreasing' ? '#cc0000' : '#0066cc');
  const trendIcon = trend.trend === 'increasing' ? <TrendingUp size={20} /> : <TrendingDown size={20} />;

  return (
    <div className="trend-analysis">
      <div className="trend-header">
        <h3>Trend Analysis</h3>
        <div className="trend-indicator" style={{ color: trendColor }}>
          {trendIcon}
          <span className="trend-label">{trend.trend.toUpperCase()}</span>
        </div>
      </div>

      <div className="trend-stats">
        <div className="stat-item">
          <span className="label">Avg Quantity</span>
          <span className="value">{trend.avg_quantity?.toFixed(0)} units</span>
        </div>
        <div className="stat-item">
          <span className="label">Volatility (Std Dev)</span>
          <span className="value">{trend.volatility?.toFixed(1)}</span>
        </div>
        <div className="stat-item">
          <span className="label">Trend Slope</span>
          <span className="value" style={{ color: trendColor }}>
            {trend.slope?.toFixed(2)} units/day
          </span>
        </div>
      </div>

      <div className="trend-chart-container">
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={trend.chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis
              dataKey="date"
              stroke="#666"
              tick={{ fontSize: 11 }}
              interval={Math.floor(trend.chartData?.length / 5)}
            />
            <YAxis stroke="#666" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #ccc',
                borderRadius: '4px',
              }}
              formatter={(value) => value.toFixed(0)}
              labelFormatter={(label) => `Date: ${label}`}
            />
            <Line
              type="monotone"
              dataKey="quantity"
              stroke={trendColor}
              dot={false}
              strokeWidth={2}
              name="Quantity"
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="trend-interpretation">
        {trend.trend === 'increasing' && (
          <p>
            Stock levels are <strong>increasing</strong>. Demand may be lower than supply, consider reviewing reorder quantities.
          </p>
        )}
        {trend.trend === 'decreasing' && (
          <p>
            Stock levels are <strong>decreasing</strong>. Demand is higher than supply, monitor closely and plan reorders.
          </p>
        )}
        {trend.trend === 'stable' && (
          <p>
            Stock levels are <strong>stable</strong>. Supply and demand are balanced.
          </p>
        )}
      </div>
    </div>
  );
};

export default TrendAnalysis;

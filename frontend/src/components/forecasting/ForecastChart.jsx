import React, { useEffect, useState } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { warehouseApi } from '../../lib/api';
import './ForecastChart.css';

const ForecastChart = ({ sku, days = 30 }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadForecast();
  }, [sku, days]);

  const loadForecast = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await warehouseApi.get(`/forecasting/demand/${sku}?days=${days}`);

      if (response.status === 'success' || response.status === 'insufficient_data') {
        // Transform forecast data for chart
        const chartData = response.forecasts.map(f => ({
          date: new Date(f.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          predicted: f.predicted_demand,
          low: f.confidence_low,
          high: f.confidence_high,
        }));
        setData({ ...response, chartData });
      } else {
        setError(response.message || 'Failed to load forecast');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="forecast-chart loading">Loading forecast...</div>;
  }

  if (error) {
    return <div className="forecast-chart error">Error: {error}</div>;
  }

  if (!data) {
    return <div className="forecast-chart empty">No forecast data</div>;
  }

  return (
    <div className="forecast-chart">
      <div className="forecast-header">
        <h3>Demand Forecast - {sku}</h3>
        <span className="forecast-model">{data.model}</span>
      </div>

      <div className="forecast-stats">
        <div className="stat">
          <span className="label">Avg Daily Demand</span>
          <span className="value">{data.average_daily_demand?.toFixed(0)} units</span>
        </div>
        <div className="stat">
          <span className="label">Recommended Reorder</span>
          <span className="value">{data.recommended_reorder_qty} units</span>
        </div>
      </div>

      <div className="forecast-chart-container">
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data.chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorRange" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#e6f2ff" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#e6f2ff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis dataKey="date" stroke="#666" />
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
            <Legend />
            <Area
              type="monotone"
              dataKey="low"
              stroke="none"
              fillOpacity={0}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="high"
              stroke="none"
              fillOpacity={0}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="predicted"
              stroke="#0066cc"
              fill="url(#colorRange)"
              name="Predicted Demand"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="forecast-note">
        Forecast confidence interval: {data.chartData[0]?.low} - {data.chartData[0]?.high} units on first day
      </div>
    </div>
  );
};

export default ForecastChart;

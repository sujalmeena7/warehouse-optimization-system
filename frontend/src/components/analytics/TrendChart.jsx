import React from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './TrendChart.css';

const TrendChart = ({ data, title, dataKeys = [], height = 300, type = 'line' }) => {
  if (!data || data.length === 0) {
    return <div className="trend-chart empty">No data available</div>;
  }

  const ChartComponent = type === 'area' ? AreaChart : LineChart;
  const DataComponent = type === 'area' ? Area : Line;
  const colors = ['#0066cc', '#00aa44', '#ff9900', '#cc0000', '#6600cc'];

  return (
    <div className="trend-chart">
      {title && <h3 className="chart-title">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <ChartComponent data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis dataKey="date" stroke="#666" />
          <YAxis stroke="#666" />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
            cursor={{ fill: 'rgba(0, 102, 204, 0.1)' }}
          />
          {dataKeys.length > 0 && <Legend />}
          {dataKeys.map((key, idx) => (
            <DataComponent
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colors[idx % colors.length]}
              fill={type === 'area' ? colors[idx % colors.length] : 'none'}
              fillOpacity={type === 'area' ? 0.2 : 1}
              isAnimationActive={false}
              name={key.replace(/_/g, ' ').toUpperCase()}
            />
          ))}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  );
};

export default TrendChart;

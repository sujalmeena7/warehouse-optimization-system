import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import './KPICard.css';

const KPICard = ({ title, value, unit = '', trend = null, icon: Icon, color = 'blue' }) => {
  const isTrendPositive = trend && trend > 0;
  const trendColor = isTrendPositive ? '#00aa44' : '#cc0000';

  return (
    <div className={`kpi-card color-${color}`}>
      <div className="kpi-header">
        <h4>{title}</h4>
        {Icon && <Icon size={18} className="kpi-icon" />}
      </div>

      <div className="kpi-value">
        <span className="value">{typeof value === 'number' && value > 1000000 ? (value / 1000000).toFixed(1) + 'M' : value}</span>
        {unit && <span className="unit">{unit}</span>}
      </div>

      {trend !== null && (
        <div className="kpi-trend" style={{ color: trendColor }}>
          {isTrendPositive ? (
            <TrendingUp size={16} />
          ) : (
            <TrendingDown size={16} />
          )}
          <span>{Math.abs(trend).toFixed(1)}%</span>
        </div>
      )}
    </div>
  );
};

export default KPICard;

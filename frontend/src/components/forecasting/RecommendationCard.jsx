import React, { useEffect, useState } from 'react';
import { AlertCircle, TrendingUp } from 'lucide-react';
import { warehouseApi } from '../../lib/api';
import './RecommendationCard.css';

const RecommendationCard = ({ sku }) => {
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadRecommendation();
  }, [sku]);

  const loadRecommendation = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await warehouseApi.get(`/forecasting/recommendation/${sku}`);
      setRecommendation(response);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="recommendation-card loading">Loading recommendation...</div>;
  }

  if (error) {
    return <div className="recommendation-card error">Error: {error}</div>;
  }

  if (!recommendation) {
    return null;
  }

  const { current_quantity, average_daily_demand, recommended_reorder_qty, reorder_threshold } = recommendation;
  const days_until_reorder = reorder_threshold > 0 ? Math.ceil((current_quantity - reorder_threshold) / average_daily_demand) : 'N/A';
  const urgency = days_until_reorder === 'N/A' ? 'low' : (days_until_reorder <= 3 ? 'high' : (days_until_reorder <= 7 ? 'medium' : 'low'));

  return (
    <div className={`recommendation-card urgency-${urgency}`}>
      <div className="card-header">
        <h3>Reorder Recommendation</h3>
        {urgency === 'high' && <AlertCircle size={20} className="urgency-icon" />}
        {urgency === 'medium' && <TrendingUp size={20} className="urgency-icon" />}
      </div>

      <div className="recommendation-content">
        <div className="rec-row">
          <span className="rec-label">Current Stock</span>
          <span className="rec-value">{current_quantity} units</span>
        </div>

        <div className="rec-row">
          <span className="rec-label">Avg Daily Demand</span>
          <span className="rec-value">{average_daily_demand.toFixed(1)} units/day</span>
        </div>

        <div className="rec-row">
          <span className="rec-label">Reorder Threshold</span>
          <span className="rec-value">{reorder_threshold} units</span>
        </div>

        <div className="rec-divider" />

        <div className="rec-row highlight">
          <span className="rec-label">Recommended Qty</span>
          <span className="rec-value">{recommended_reorder_qty} units</span>
        </div>

        {days_until_reorder !== 'N/A' && (
          <div className="rec-row">
            <span className="rec-label">Days Until Reorder</span>
            <span className={`rec-value urgency-${urgency}`}>
              {days_until_reorder} days
            </span>
          </div>
        )}

        <div className="rec-status">
          {urgency === 'high' && (
            <span className="status-badge critical">
              Urgent - Reorder recommended immediately
            </span>
          )}
          {urgency === 'medium' && (
            <span className="status-badge warning">
              Monitor - Plan reorder soon
            </span>
          )}
          {urgency === 'low' && (
            <span className="status-badge healthy">
              Healthy - Stock levels normal
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default RecommendationCard;

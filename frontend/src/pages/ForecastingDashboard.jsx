import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import ForecastChart from '@/components/forecasting/ForecastChart';
import RecommendationCard from '@/components/forecasting/RecommendationCard';
import TrendAnalysis from '@/components/forecasting/TrendAnalysis';
import AnomalyAlert from '@/components/forecasting/AnomalyAlert';
import { useAuth } from '@/hooks/useAuth';
import './ForecastingDashboard.css';

const ForecastingDashboard = () => {
  const { user } = useAuth();
  const [selectedSku, setSelectedSku] = useState('');
  const [forecastDays, setForecastDays] = useState(30);
  const [trendDays, setTrendDays] = useState(90);
  const [showAllAnomalies, setShowAllAnomalies] = useState(false);

  const handleSkuSubmit = (e) => {
    e.preventDefault();
    if (selectedSku.trim()) {
      setSelectedSku(selectedSku.trim());
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="forecasting-dashboard"
    >
      <div className="dashboard-header">
        <div>
          <h1>Demand Forecasting</h1>
          <p className="subtitle">Predict inventory needs and identify pattern anomalies</p>
        </div>
      </div>

      <Card className="forecasting-controls">
        <CardContent className="pt-6">
          <form onSubmit={handleSkuSubmit} className="controls-form">
            <div className="form-group">
              <label htmlFor="sku-input">Product SKU</label>
              <input
                id="sku-input"
                type="text"
                value={selectedSku}
                onChange={(e) => setSelectedSku(e.target.value)}
                placeholder="Enter SKU (e.g., SKU-001)"
                className="sku-input"
              />
            </div>

            <div className="form-group">
              <label htmlFor="forecast-days">Forecast Days</label>
              <select
                id="forecast-days"
                value={forecastDays}
                onChange={(e) => setForecastDays(parseInt(e.target.value))}
                className="days-select"
              >
                <option value="7">7 Days</option>
                <option value="14">14 Days</option>
                <option value="30">30 Days</option>
                <option value="60">60 Days</option>
                <option value="90">90 Days</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="trend-days">Trend Analysis Period</label>
              <select
                id="trend-days"
                value={trendDays}
                onChange={(e) => setTrendDays(parseInt(e.target.value))}
                className="days-select"
              >
                <option value="30">30 Days</option>
                <option value="60">60 Days</option>
                <option value="90">90 Days</option>
                <option value="180">6 Months</option>
              </select>
            </div>

            <button type="submit" className="submit-btn">
              Analyze
            </button>
          </form>
        </CardContent>
      </Card>

      {selectedSku && (
        <>
          <div className="dashboard-grid two-col">
            <Card className="card-container">
              <CardHeader>
                <CardTitle>Forecast & Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <ForecastChart sku={selectedSku} days={forecastDays} />
              </CardContent>
            </Card>

            <Card className="card-container">
              <CardHeader>
                <CardTitle>Reorder Strategy</CardTitle>
              </CardHeader>
              <CardContent>
                <RecommendationCard sku={selectedSku} />
              </CardContent>
            </Card>
          </div>

          <Card className="card-container">
            <CardHeader>
              <CardTitle>Historical Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <TrendAnalysis sku={selectedSku} days={trendDays} />
            </CardContent>
          </Card>
        </>
      )}

      <Card className="card-container">
        <CardHeader>
          <CardTitle>Inventory Anomalies</CardTitle>
        </CardHeader>
        <CardContent>
          <AnomalyAlert sku={selectedSku || null} />
        </CardContent>
      </Card>

      {!selectedSku && (
        <Card className="empty-state">
          <CardContent className="pt-6">
            <div className="empty-content">
              <p>👆 Select a SKU above to start forecasting</p>
              <p>Or view system-wide anomalies below</p>
            </div>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
};

export default ForecastingDashboard;

import React, { useEffect, useState } from 'react';
import { AlertTriangle, AlertCircle } from 'lucide-react';
import { warehouseApi } from '../../lib/api';
import './AnomalyAlert.css';

const AnomalyAlert = ({ sku = null }) => {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAnomalies();
  }, [sku]);

  const loadAnomalies = async () => {
    try {
      setLoading(true);
      setError(null);

      const url = sku ? `/forecasting/anomalies?sku=${sku}` : '/forecasting/anomalies';
      const response = await warehouseApi.get(url);

      if (response.status === 'success') {
        setAnomalies(response.anomalies || []);
      } else if (response.status === 'insufficient_data') {
        setAnomalies([]);
      } else {
        setError(response.message || 'Failed to load anomalies');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="anomaly-alert loading">Detecting anomalies...</div>;
  }

  if (error) {
    return <div className="anomaly-alert error">Error: {error}</div>;
  }

  if (anomalies.length === 0) {
    return (
      <div className="anomaly-alert empty">
        <AlertCircle size={20} />
        <p>No anomalies detected - inventory patterns are normal</p>
      </div>
    );
  }

  return (
    <div className="anomaly-alert">
      <div className="alert-header">
        <h3>
          <AlertTriangle size={18} />
          Detected Anomalies ({anomalies.length})
        </h3>
        <button onClick={loadAnomalies} className="refresh-btn" title="Refresh">
          ↻
        </button>
      </div>

      <div className="anomaly-list">
        {anomalies.map((anomaly, idx) => (
          <div
            key={idx}
            className={`anomaly-item severity-${anomaly.severity}`}
          >
            <div className="anomaly-left">
              <div className="anomaly-date">
                {new Date(anomaly.date).toLocaleDateString()} {new Date(anomaly.date).toLocaleTimeString()}
              </div>
              {anomaly.sku && <div className="anomaly-sku">SKU: {anomaly.sku}</div>}
            </div>

            <div className="anomaly-center">
              <div className="anomaly-data">
                <span className="label">Actual:</span>
                <span className="value">{anomaly.quantity} units</span>
              </div>
              <div className="anomaly-data">
                <span className="label">Expected:</span>
                <span className="value">{anomaly.expected} units</span>
              </div>
            </div>

            <div className="anomaly-right">
              <span className={`severity-badge ${anomaly.severity}`}>
                {anomaly.severity.toUpperCase()}
              </span>
              <span className="z-score">Z: {anomaly.z_score.toFixed(2)}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="anomaly-note">
        Anomalies are detected when inventory deviates significantly from the expected pattern using statistical analysis.
      </div>
    </div>
  );
};

export default AnomalyAlert;

import React, { useState, useEffect } from 'react';
import { warehouseApi } from '../../lib/api';
import './ExportDialog.css';

const ExportDialog = ({ entityType, filters = null, isOpen, onClose }) => {
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [availableColumns, setAvailableColumns] = useState([]);
  const [format, setFormat] = useState('csv');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadAvailableColumns();
      // Select all columns by default
      loadAvailableColumns().then((cols) => {
        if (cols) setSelectedColumns(cols);
      });
    }
  }, [isOpen, entityType]);

  const loadAvailableColumns = async () => {
    try {
      const cols = await warehouseApi.get(`/export/columns/${entityType}`);
      setAvailableColumns(cols);
      setSelectedColumns(cols); // Select all by default
      return cols;
    } catch (err) {
      setError(err.message);
      return null;
    }
  };

  const handleColumnToggle = (column) => {
    setSelectedColumns(prev =>
      prev.includes(column)
        ? prev.filter(c => c !== column)
        : [...prev, column]
    );
  };

  const handleSelectAll = () => {
    setSelectedColumns(availableColumns);
  };

  const handleDeselectAll = () => {
    setSelectedColumns([]);
  };

  const handleExport = async () => {
    if (selectedColumns.length === 0) {
      setError('Please select at least one column');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const exportData = {
        entity_type: entityType,
        format: format,
        selected_columns: selectedColumns,
        filters: filters,
      };

      // Make the export request
      const response = await fetch(`${warehouseApi.baseURL}/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
        body: JSON.stringify(exportData),
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      // Get the filename from headers
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `export_${Date.now()}.${format}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=([^;]+)/);
        if (match) filename = match[1];
      }

      // Download the file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="export-dialog-overlay" onClick={onClose}>
      <div className="export-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h2>Export {entityType.charAt(0).toUpperCase() + entityType.slice(1)}</h2>
          <button onClick={onClose} className="close-button">✕</button>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="dialog-body">
          <div className="format-section">
            <label>Format</label>
            <div className="format-options">
              <label className="radio-option">
                <input
                  type="radio"
                  value="csv"
                  checked={format === 'csv'}
                  onChange={(e) => setFormat(e.target.value)}
                />
                CSV
              </label>
              <label className="radio-option">
                <input
                  type="radio"
                  value="excel"
                  checked={format === 'excel'}
                  onChange={(e) => setFormat(e.target.value)}
                  disabled
                />
                Excel (Coming Soon)
              </label>
            </div>
          </div>

          <div className="columns-section">
            <div className="columns-header">
              <label>Select Columns to Export</label>
              <div className="column-actions">
                <button onClick={handleSelectAll} className="text-button">
                  Select All
                </button>
                <span className="separator">|</span>
                <button onClick={handleDeselectAll} className="text-button">
                  Deselect All
                </button>
              </div>
            </div>

            <div className="columns-list">
              {availableColumns.map((col) => (
                <label key={col} className="column-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedColumns.includes(col)}
                    onChange={() => handleColumnToggle(col)}
                  />
                  <span className="column-name">
                    {col.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </label>
              ))}
            </div>

            <div className="selected-count">
              {selectedColumns.length} of {availableColumns.length} columns selected
            </div>
          </div>
        </div>

        <div className="dialog-footer">
          <button onClick={onClose} className="cancel-button">
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={loading || selectedColumns.length === 0}
            className="export-button"
          >
            {loading ? 'Exporting...' : 'Export'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExportDialog;

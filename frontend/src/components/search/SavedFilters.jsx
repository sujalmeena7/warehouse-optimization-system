import React, { useState, useEffect } from 'react';
import { warehouseApi } from '../../lib/api';
import './SavedFilters.css';

const SavedFilters = ({ entityType, onSelectFilter }) => {
  const [savedFilters, setSavedFilters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [newFilterName, setNewFilterName] = useState('');
  const [currentFilters, setCurrentFilters] = useState(null);

  useEffect(() => {
    loadSavedFilters();
  }, [entityType]);

  const loadSavedFilters = async () => {
    try {
      setLoading(true);
      const filters = await warehouseApi.get(`/saved-filters?entity_type=${entityType}`);
      setSavedFilters(filters);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveNewFilter = async () => {
    if (!newFilterName || !currentFilters) {
      alert('Please enter a filter name and apply filters first');
      return;
    }

    try {
      await warehouseApi.post('/saved-filters', {
        name: newFilterName,
        entity_type: entityType,
        filters: currentFilters,
      });
      setNewFilterName('');
      setShowForm(false);
      loadSavedFilters();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteFilter = async (filterId) => {
    if (!window.confirm('Delete this saved filter?')) return;

    try {
      await warehouseApi.delete(`/saved-filters/${filterId}`);
      loadSavedFilters();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUseFilter = (filter) => {
    onSelectFilter(filter.filters);
  };

  return (
    <div className="saved-filters">
      <div className="filters-header">
        <h3>Saved Filters</h3>
        <button onClick={() => setShowForm(!showForm)} className="toggle-form-button">
          {showForm ? '✕' : '+ New'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {showForm && (
        <div className="save-filter-form">
          <input
            type="text"
            placeholder="Filter name (e.g., 'Low Stock Items')"
            value={newFilterName}
            onChange={(e) => setNewFilterName(e.target.value)}
          />
          <button onClick={handleSaveNewFilter} className="save-button">
            Save Current Filter
          </button>
        </div>
      )}

      {loading ? (
        <div className="loading">Loading filters...</div>
      ) : savedFilters.length === 0 ? (
        <div className="no-filters">No saved filters yet</div>
      ) : (
        <div className="filters-list">
          {savedFilters.map((filter) => (
            <div key={filter.id} className="filter-item">
              <div className="filter-info">
                <h4>{filter.name}</h4>
                <span className="filter-date">
                  {new Date(filter.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="filter-actions">
                <button
                  onClick={() => handleUseFilter(filter)}
                  className="use-button"
                  title="Apply this filter"
                >
                  Use
                </button>
                <button
                  onClick={() => handleDeleteFilter(filter.id)}
                  className="delete-button"
                  title="Delete this filter"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SavedFilters;

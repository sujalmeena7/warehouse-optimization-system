import React, { useState } from 'react';
import './FilterPanel.css';

const FilterPanel = ({ entityType, onApplyFilters, onClose }) => {
  const [filters, setFilters] = useState({
    category: '',
    zone: '',
    status: '',
    priority: '',
    qty_min: '',
    qty_max: '',
  });

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleApplyFilters = () => {
    // Filter out empty values
    const activeFilters = Object.fromEntries(
      Object.entries(filters).filter(([_, v]) => v !== '')
    );
    onApplyFilters(activeFilters);
  };

  const handleClearFilters = () => {
    setFilters({
      category: '',
      zone: '',
      status: '',
      priority: '',
      qty_min: '',
      qty_max: '',
    });
  };

  return (
    <div className="filter-panel">
      <div className="filter-header">
        <h3>Advanced Filters</h3>
        <button onClick={onClose} className="close-button">✕</button>
      </div>

      <div className="filter-body">
        {entityType === 'inventory' ? (
          <>
            <div className="filter-group">
              <label>Category</label>
              <select
                name="category"
                value={filters.category}
                onChange={handleFilterChange}
              >
                <option value="">All Categories</option>
                <option value="Hardware">Hardware</option>
                <option value="Electronics">Electronics</option>
                <option value="Software">Software</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Zone</label>
              <select
                name="zone"
                value={filters.zone}
                onChange={handleFilterChange}
              >
                <option value="">All Zones</option>
                <option value="A">Zone A</option>
                <option value="B">Zone B</option>
                <option value="C">Zone C</option>
                <option value="D">Zone D</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Stock Status</label>
              <select
                name="status"
                value={filters.status}
                onChange={handleFilterChange}
              >
                <option value="">All Statuses</option>
                <option value="healthy">Healthy</option>
                <option value="low">Low Stock</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Quantity Range</label>
              <div className="range-inputs">
                <input
                  type="number"
                  name="qty_min"
                  placeholder="Min"
                  value={filters.qty_min}
                  onChange={handleFilterChange}
                />
                <span>to</span>
                <input
                  type="number"
                  name="qty_max"
                  placeholder="Max"
                  value={filters.qty_max}
                  onChange={handleFilterChange}
                />
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="filter-group">
              <label>Status</label>
              <select
                name="status"
                value={filters.status}
                onChange={handleFilterChange}
              >
                <option value="">All Statuses</option>
                <option value="queued">Queued</option>
                <option value="picking">Picking</option>
                <option value="packed">Packed</option>
                <option value="shipped">Shipped</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Priority</label>
              <select
                name="priority"
                value={filters.priority}
                onChange={handleFilterChange}
              >
                <option value="">All Priorities</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </>
        )}
      </div>

      <div className="filter-actions">
        <button onClick={handleClearFilters} className="clear-button">
          Clear Filters
        </button>
        <button onClick={handleApplyFilters} className="apply-button">
          Apply Filters
        </button>
      </div>
    </div>
  );
};

export default FilterPanel;

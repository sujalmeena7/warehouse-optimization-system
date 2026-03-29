import React, { useState } from 'react';
import './AdvancedSearch.css';

const AdvancedSearch = ({ onSearch, onShowFilters }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [entityType, setEntityType] = useState('inventory');

  const handleSearch = (e) => {
    e.preventDefault();
    onSearch({ query: searchQuery, entityType });
  };

  return (
    <div className="advanced-search">
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-group">
          <select
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
            className="entity-type-select"
          >
            <option value="inventory">Inventory</option>
            <option value="orders">Orders</option>
          </select>

          <input
            type="text"
            placeholder={`Search ${entityType}...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />

          <button type="submit" className="search-button">
            🔍 Search
          </button>
        </div>
      </form>

      <button onClick={onShowFilters} className="filters-button">
        ⚙️ Advanced Filters
      </button>
    </div>
  );
};

export default AdvancedSearch;

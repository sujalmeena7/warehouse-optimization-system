import React, { useState, useCallback } from 'react';
import AdvancedSearch from '../components/search/AdvancedSearch';
import FilterPanel from '../components/search/FilterPanel';
import SearchResults from '../components/search/SearchResults';
import SavedFilters from '../components/search/SavedFilters';
import { warehouseApi } from '../lib/api';
import './SearchPage.css';

const SearchPage = () => {
  const [searchResults, setSearchResults] = useState(null);
  const [entityType, setEntityType] = useState('inventory');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [currentFilters, setCurrentFilters] = useState(null);

  const handleSearch = useCallback(async (searchData) => {
    try {
      setLoading(true);
      setError(null);
      setEntityType(searchData.entityType);

      let endpoint = searchData.entityType === 'inventory'
        ? '/search/inventory'
        : '/search/orders';

      const params = new URLSearchParams();
      if (searchData.query) {
        params.append('q', searchData.query);
      }

      // Add filter parameters
      if (currentFilters) {
        if (searchData.entityType === 'inventory') {
          if (currentFilters.category) params.append('category', currentFilters.category);
          if (currentFilters.zone) params.append('zone', currentFilters.zone);
          if (currentFilters.status) params.append('status', currentFilters.status);
          if (currentFilters.qty_min || currentFilters.qty_max) {
            const range = {};
            if (currentFilters.qty_min) range.min = parseInt(currentFilters.qty_min);
            if (currentFilters.qty_max) range.max = parseInt(currentFilters.qty_max);
            params.append('qty_range', JSON.stringify(range));
          }
        } else {
          if (currentFilters.status) params.append('status', currentFilters.status);
          if (currentFilters.priority) params.append('priority', currentFilters.priority);
        }
      }

      const results = await warehouseApi.get(`${endpoint}?${params.toString()}`);
      setSearchResults(results);
      setShowFilters(false);
    } catch (err) {
      setError(err.message);
      setSearchResults(null);
    } finally {
      setLoading(false);
    }
  }, [currentFilters]);

  const handleApplyFilters = (filters) => {
    setCurrentFilters(filters);
    setShowFilters(false);
  };

  const handleSelectSavedFilter = (filters) => {
    setCurrentFilters(filters);
  };

  return (
    <div className="search-page">
      <div className="search-container">
        <div className="search-main">
          <h1>Advanced Search</h1>

          <AdvancedSearch
            onSearch={handleSearch}
            onShowFilters={() => setShowFilters(!showFilters)}
          />

          {showFilters && (
            <FilterPanel
              entityType={entityType}
              onApplyFilters={handleApplyFilters}
              onClose={() => setShowFilters(false)}
            />
          )}

          <SearchResults
            results={searchResults}
            entityType={entityType}
            loading={loading}
            error={error}
          />
        </div>

        <div className="search-sidebar">
          <SavedFilters
            entityType={entityType}
            onSelectFilter={handleSelectSavedFilter}
          />
        </div>
      </div>
    </div>
  );
};

export default SearchPage;

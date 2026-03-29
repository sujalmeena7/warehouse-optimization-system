import React from 'react';
import './SearchResults.css';

const SearchResults = ({ results, entityType, loading, error }) => {
  if (loading) {
    return <div className="search-results loading">Searching...</div>;
  }

  if (error) {
    return <div className="search-results error">Error: {error}</div>;
  }

  if (!results || (entityType === 'inventory' ? !results.items : !results.orders)) {
    return <div className="search-results empty">No results found. Try a different search.</div>;
  }

  const items = entityType === 'inventory' ? results.items : results.orders;
  const total = results.total || 0;

  return (
    <div className="search-results">
      <div className="results-header">
        <h3>Results</h3>
        <span className="result-count">{total} items found</span>
      </div>

      <div className="results-table">
        {entityType === 'inventory' ? (
          <table>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Name</th>
                <th>Category</th>
                <th>Quantity</th>
                <th>Status</th>
                <th>Zone</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.sku}</td>
                  <td>{item.name}</td>
                  <td>{item.category}</td>
                  <td>{item.quantity}</td>
                  <td>
                    <span className={`status-badge status-${item.stock_status || 'healthy'}`}>
                      {item.stock_status || 'Healthy'}
                    </span>
                  </td>
                  <td>{item.zone}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Destination</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Items</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.reference}</td>
                  <td>{item.destination}</td>
                  <td>
                    <span className={`status-badge status-${item.status}`}>
                      {item.status}
                    </span>
                  </td>
                  <td>
                    <span className={`priority-badge priority-${item.priority}`}>
                      {item.priority}
                    </span>
                  </td>
                  <td>{item.items?.length || 0}</td>
                  <td>{new Date(item.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {total > items.length && (
        <div className="pagination-info">
          Showing {items.length} of {total} results
        </div>
      )}
    </div>
  );
};

export default SearchResults;

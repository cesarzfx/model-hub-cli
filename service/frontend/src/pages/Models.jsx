// service/frontend/src/pages/Models.jsx
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { listPackages } from '../api/packages';
import './Models.css';

export default function Models() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [versionFilter, setVersionFilter] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [limit] = useState(50);
  const { logout } = useAuth();

  useEffect(() => {
    loadPackages();
  }, [page, searchQuery, versionFilter]);

  const loadPackages = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        limit,
      };
      if (searchQuery) {
        params.q = searchQuery;
      }
      if (versionFilter) {
        params.version = versionFilter;
      }
      const data = await listPackages(params);
      setPackages(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error('Error loading packages:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    loadPackages();
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="models-container">
      <header className="models-header">
        <h1>Trustworthy Model Registry</h1>
        <div className="header-actions">
          <Link to="/submit" className="btn btn-primary">Submit Model</Link>
          <button onClick={logout} className="btn btn-secondary">Logout</button>
        </div>
      </header>

      <div className="models-content">
        <div className="filters">
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              placeholder="Search models (regex)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            <input
              type="text"
              placeholder="Version filter (e.g., 1.2.3, ~1.2.0, ^1.2.0)"
              value={versionFilter}
              onChange={(e) => setVersionFilter(e.target.value)}
              className="version-input"
            />
            <button type="submit" className="btn btn-search">Search</button>
          </form>
        </div>

        {loading ? (
          <div className="loading">Loading models...</div>
        ) : (
          <>
            <div className="models-grid">
              {packages.map((pkg) => (
                <Link key={pkg.id} to={`/models/${pkg.id}`} className="model-card">
                  <h3>{pkg.name}</h3>
                  <p className="version">v{pkg.version}</p>
                  <div className="scores">
                    <div className="score-item">
                      <span className="score-label">Net Score:</span>
                      <span className="score-value">
                        {pkg.scores?.availability || pkg.scores?.license || 'N/A'}
                      </span>
                    </div>
                    <div className="score-details">
                      {pkg.scores?.license && (
                        <span>License: {pkg.scores.license.toFixed(2)}</span>
                      )}
                      {pkg.scores?.ramp_up && (
                        <span>Ramp Up: {pkg.scores.ramp_up.toFixed(2)}</span>
                      )}
                    </div>
                  </div>
                  <p className="size">{pkg.size_bytes ? `${(pkg.size_bytes / 1024 / 1024).toFixed(2)} MB` : 'Size unknown'}</p>
                </Link>
              ))}
            </div>

            {packages.length === 0 && (
              <div className="no-results">No models found</div>
            )}

            {totalPages > 1 && (
              <div className="pagination">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="btn btn-pagination"
                >
                  Previous
                </button>
                <span className="page-info">
                  Page {page} of {totalPages} (Total: {total})
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="btn btn-pagination"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}


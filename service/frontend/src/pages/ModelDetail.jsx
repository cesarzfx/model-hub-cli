// service/frontend/src/pages/ModelDetail.jsx
import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPackage, ratePackage, getNDJSON } from '../api/packages';
import './ModelDetail.css';

export default function ModelDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [pkg, setPkg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rating, setRating] = useState(false);
  const [ndjson, setNdjson] = useState(null);

  useEffect(() => {
    loadPackage();
  }, [id]);

  const loadPackage = async () => {
    setLoading(true);
    try {
      const data = await getPackage(id);
      setPkg(data);
    } catch (error) {
      console.error('Error loading package:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRate = async () => {
    setRating(true);
    try {
      await ratePackage(id);
      await loadPackage();
    } catch (error) {
      console.error('Error rating package:', error);
    } finally {
      setRating(false);
    }
  };

  const handleDownloadNDJSON = async () => {
    try {
      const data = await getNDJSON(id);
      setNdjson(data);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${pkg.name}-${pkg.version}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading NDJSON:', error);
    }
  };

  if (loading) {
    return <div className="loading">Loading model details...</div>;
  }

  if (!pkg) {
    return <div className="error">Model not found</div>;
  }

  const scores = pkg.scores || {};
  const isContributor = user?.role === 'contributor' || user?.role === 'admin';

  return (
    <div className="model-detail-container">
      <header className="detail-header">
        <div>
          <Link to="/models" className="back-link">← Back to Models</Link>
          <h1>{pkg.name}</h1>
          <p className="version">Version: {pkg.version}</p>
        </div>
        <div className="header-actions">
          {isContributor && (
            <button onClick={handleRate} disabled={rating} className="btn btn-primary">
              {rating ? 'Rating...' : 'Rate Model'}
            </button>
          )}
          <button onClick={handleDownloadNDJSON} className="btn btn-secondary">
            Download NDJSON
          </button>
          <button onClick={logout} className="btn btn-secondary">Logout</button>
        </div>
      </header>

      <div className="detail-content">
        <div className="detail-section">
          <h2>Metadata</h2>
          {pkg.card_text && (
            <div className="card-text">
              <h3>Card Text</h3>
              <pre>{pkg.card_text}</pre>
            </div>
          )}
          {pkg.meta && Object.keys(pkg.meta).length > 0 && (
            <div className="meta">
              <h3>Metadata</h3>
              <pre>{JSON.stringify(pkg.meta, null, 2)}</pre>
            </div>
          )}
        </div>

        <div className="detail-section">
          <h2>Scores</h2>
          <div className="scores-grid">
            {Object.entries(scores).map(([key, value]) => {
              if (value === null || value === undefined) return null;
              const numValue = typeof value === 'number' ? value : 0;
              const percentage = (numValue * 100).toFixed(1);
              return (
                <div key={key} className="score-card">
                  <div className="score-header">
                    <span className="score-name">{key.replace(/_/g, ' ').toUpperCase()}</span>
                    <span className="score-value">{numValue.toFixed(3)}</span>
                  </div>
                  <div className="score-bar">
                    <div
                      className="score-bar-fill"
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                  <span className="score-percentage">{percentage}%</span>
                </div>
              );
            })}
          </div>
        </div>

        {pkg.parents && pkg.parents.length > 0 && (
          <div className="detail-section">
            <h2>Parents</h2>
            <ul>
              {pkg.parents.map((parentId) => (
                <li key={parentId}>
                  <Link to={`/models/${parentId}`}>{parentId}</Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}


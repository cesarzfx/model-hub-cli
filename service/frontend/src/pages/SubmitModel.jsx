// service/frontend/src/pages/SubmitModel.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { submitCLI } from '../api/packages';
import './SubmitModel.css';

export default function SubmitModel() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [codeUrl, setCodeUrl] = useState('');
  const [datasetUrl, setDatasetUrl] = useState('');
  const [modelUrl, setModelUrl] = useState('');
  const [name, setName] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess(null);

    if (!modelUrl) {
      setError('Model URL is required');
      return;
    }

    setLoading(true);
    try {
      const result = await submitCLI({
        code_url: codeUrl || null,
        dataset_url: datasetUrl || null,
        model_url: modelUrl,
        name: name || null,
        version: version || '1.0.0',
      });
      setSuccess(result);
      setTimeout(() => {
        navigate(`/models/${result.id}`);
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit model');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="submit-container">
      <header className="submit-header">
        <h1>Submit Model</h1>
        <div className="header-actions">
          <button onClick={() => navigate('/models')} className="btn btn-secondary">
            Cancel
          </button>
          <button onClick={logout} className="btn btn-secondary">Logout</button>
        </div>
      </header>

      <div className="submit-content">
        <div className="submit-box">
          <p className="instructions">
            Submit a model using CLI-style format. Provide 3 URLs: code repository, dataset, and model.
            Model URL is required; code and dataset URLs are optional.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="code_url">Code Repository URL (Optional)</label>
              <input
                type="url"
                id="code_url"
                value={codeUrl}
                onChange={(e) => setCodeUrl(e.target.value)}
                placeholder="https://github.com/org/repo"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="dataset_url">Dataset URL (Optional)</label>
              <input
                type="url"
                id="dataset_url"
                value={datasetUrl}
                onChange={(e) => setDatasetUrl(e.target.value)}
                placeholder="https://huggingface.co/datasets/org/dataset"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="model_url">
                Model URL <span className="required">*</span>
              </label>
              <input
                type="url"
                id="model_url"
                value={modelUrl}
                onChange={(e) => setModelUrl(e.target.value)}
                placeholder="https://huggingface.co/org/model"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="name">Model Name (Optional)</label>
              <input
                type="text"
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Will be extracted from URL if not provided"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="version">Version</label>
              <input
                type="text"
                id="version"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="1.0.0"
                disabled={loading}
              />
            </div>

            {error && <div className="error-message">{error}</div>}
            {success && (
              <div className="success-message">
                Model submitted successfully! Redirecting to model details...
                <div className="success-details">
                  ID: {success.id}, Name: {success.name}
                </div>
              </div>
            )}

            <button type="submit" disabled={loading} className="btn btn-primary btn-submit">
              {loading ? 'Submitting...' : 'Submit Model'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}


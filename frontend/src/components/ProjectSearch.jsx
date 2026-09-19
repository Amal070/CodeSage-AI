import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProjectSearch() {
  const { projectId } = useParams();
  const { token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();

  // Query & Options state
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [hasSearched, setHasSearched] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState(null);
  const [searchError, setSearchError] = useState(null);

  // Vector Index Status State
  const [indexStatus, setIndexStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [buildingIndex, setBuildingIndex] = useState(false);
  const [buildMessage, setBuildMessage] = useState(null);
  const [buildError, setBuildError] = useState(null);

  // Project details
  const [projectName, setProjectName] = useState('');

  // Sample quick queries for fast demonstration & testing
  const sampleQueries = [
    'Where is JWT authentication implemented?',
    'How does the application connect to PostgreSQL?',
    'Where are uploaded ZIP files extracted?',
    'Which function handles JWT token creation?',
    'How are password hashes verified?',
  ];

  // 1. Fetch Project Details
  const fetchProject = useCallback(async () => {
    if (!token || !projectId) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (res.ok) {
        const data = await res.json();
        const pName = data.name || `Project #${projectId}`;
        setProjectName(pName);
        localStorage.setItem('codesage_active_project', String(projectId));
        localStorage.setItem('codesage_active_project_name', pName);
      }
    } catch {
      // ignore
    }
  }, [BACKEND_URL, projectId, token, logout, navigate]);

  // 2. Fetch Vector Index Status
  const fetchIndexStatus = useCallback(async () => {
    if (!token || !projectId) return;
    setLoadingStatus(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/vector-index/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setIndexStatus(data);
      }
    } catch {
      // ignore
    } finally {
      setLoadingStatus(false);
    }
  }, [BACKEND_URL, projectId, token, logout, navigate]);

  // 3. Build / Rebuild Vector Index
  const triggerBuildIndex = async () => {
    if (!token || !projectId || buildingIndex) return;
    setBuildingIndex(true);
    setBuildError(null);
    setBuildMessage(null);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/vector-index`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to prepare code search index.');
      }

      setBuildMessage(
        `Search index updated successfully: ${data.indexed_vectors} code sections indexed.`
      );
      fetchIndexStatus();
    } catch (err) {
      setBuildError(err.message || 'An error occurred while preparing the search index.');
    } finally {
      setBuildingIndex(false);
    }
  };

  // 4. Perform Semantic Search
  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    const cleanQuery = query.trim();
    if (!cleanQuery) {
      setSearchError('Search query cannot be empty.');
      return;
    }

    setSearching(true);
    setSearchError(null);
    setHasSearched(true);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: cleanQuery,
          top_k: parseInt(topK, 10) || 5,
        }),
      });

      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Search failed.');
      }

      setSearchResults(data);
    } catch (err) {
      setSearchError(err.message || 'Semantic search failed.');
      setSearchResults(null);
    } finally {
      setSearching(false);
    }
  };

  useEffect(() => {
    fetchProject();
    fetchIndexStatus();
  }, [fetchProject, fetchIndexStatus]);

  const isIndexReady = indexStatus && indexStatus.status === 'ready' && indexStatus.indexed_vectors > 0;

  return (
    <div className="semantic-search-container animate-fade-in" id="semantic-search-page">
      {/* Top Header / Breadcrumbs */}
      <header className="analysis-header glass-card">
        <div className="analysis-title-group">
          <div className="analysis-breadcrumb font-mono">
            <Link to="/dashboard/projects" className="breadcrumb-link">Projects</Link>
            <span className="breadcrumb-sep">/</span>
            <Link to={`/dashboard/projects/${projectId}`} className="breadcrumb-link">{projectName || `Project #${projectId}`}</Link>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-current text-purple">Search Code</span>
          </div>
          <h1 className="analysis-project-name">
            Search Your Code
          </h1>
          <p className="analysis-subtitle">
            Search your project with natural language to find relevant code quickly.
          </p>
        </div>

        <div className="analysis-actions">
          <Link
            to={`/dashboard/projects/${projectId}/analysis`}
            className="btn btn-secondary btn-sm"
            id="back-to-analysis-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            <span>Project Analysis</span>
          </Link>

          <Link
            to={`/dashboard/projects/${projectId}/ask`}
            className="btn btn-secondary btn-sm"
            id="go-to-ask-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span>Ask CodeSage</span>
          </Link>

          <Link
            to={`/dashboard/projects/${projectId}/chat`}
            className="btn btn-primary btn-sm"
            id="go-to-chat-btn"
            style={{
              background: 'linear-gradient(135deg, #9333ea, #6366f1)',
              borderColor: '#a855f7',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>AI Chat</span>
          </Link>

          <Link
            to={`/dashboard/projects/${projectId}/explorer`}
            className="btn btn-secondary btn-sm"
            id="go-to-explorer-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"></polyline>
              <polyline points="8 6 2 12 8 18"></polyline>
            </svg>
            <span>Explore Code</span>
          </Link>
        </div>
      </header>

      {/* Vector Index Status Banner */}
      <section className="glass-card vector-status-card" id="vector-index-status-card">
        <div className="vector-status-content">
          <div className="indexing-icon-wrap" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
          </div>
          <div>
            <div className="indexing-title-row">
              <h3 className="indexing-title">Code Search Status</h3>
              {loadingStatus ? (
                <span className="badge badge-purple font-mono animate-pulse">Checking status...</span>
              ) : isIndexReady ? (
                <span className="badge badge-success font-mono" id="vector-status-badge">
                  Ready to search ({indexStatus.indexed_vectors} code sections indexed)
                </span>
              ) : indexStatus?.status === 'stale' ? (
                <span className="badge badge-warning font-mono" id="vector-status-badge">
                  Search Index Update Available ({indexStatus.indexed_vectors} indexed vs {indexStatus.embedded_chunks} prepared)
                </span>
              ) : (
                <span className="badge badge-warning font-mono" id="vector-status-badge">
                  Search Index Not Ready
                </span>
              )}
            </div>
            <p className="text-secondary font-mono text-xs" style={{ marginTop: '4px' }}>
              Search functions, classes, and logic across your entire project.
            </p>
          </div>
        </div>

        <div className="vector-status-actions">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={triggerBuildIndex}
            disabled={buildingIndex || loadingStatus}
            id="build-index-btn"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={buildingIndex ? 'animate-spin' : ''}
            >
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span>
              {buildingIndex
                ? 'Preparing Code Search...'
                : isIndexReady
                ? 'Update Search Index'
                : 'Enable Code Search'}
            </span>
          </button>
        </div>
      </section>

      {/* Build Success Banner */}
      {buildMessage && (
        <div className="indexing-success-banner glass-subcard animate-fade-in" id="index-build-success">
          <div className="alert-icon text-success">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
          </div>
          <div className="font-mono text-sm">
            <strong>Index Build Complete:</strong> {buildMessage}
          </div>
        </div>
      )}

      {/* Build Error Banner */}
      {buildError && (
        <div className="indexing-error-banner glass-subcard animate-fade-in" id="index-build-error">
          <div className="alert-icon text-error">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <div className="font-mono text-sm text-error">
            <strong>Index Build Error:</strong> {buildError}
          </div>
        </div>
      )}

      {/* Search Input Card */}
      <section className="search-box-card glass-card" id="search-input-section">
        <form onSubmit={handleSearch} className="search-form" id="search-form">
          <div className="search-input-wrapper">
            <div className="search-icon-inside">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </div>
            <input
              type="text"
              className="search-main-input font-mono"
              placeholder="Ask a question about the code (e.g., Where is JWT authentication implemented?)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={searching}
              id="semantic-query-input"
            />
            {query && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={() => setQuery('')}
                title="Clear input"
              >
                &times;
              </button>
            )}
          </div>

          <div className="search-options-row">
            <div className="search-k-selector">
              <label htmlFor="top-k-select" className="search-k-label font-mono text-xs text-secondary">
                Results:
              </label>
              <select
                id="top-k-select"
                className="search-k-select font-mono"
                value={topK}
                onChange={(e) => setTopK(e.target.value)}
                disabled={searching}
              >
                <option value="3">3 Results</option>
                <option value="5">5 Results (Default)</option>
                <option value="10">10 Results</option>
                <option value="15">15 Results</option>
                <option value="20">20 Results (Max)</option>
              </select>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={searching || !query.trim()}
              id="submit-search-btn"
            >
              {searching ? (
                <>
                  <div className="loading-spinner-sm" style={{ width: '16px', height: '16px' }}></div>
                  <span>Searching code...</span>
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                  <span>Search Code</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Quick Sample Queries */}
        <div className="sample-queries-wrap">
          <span className="sample-label font-mono text-xs text-secondary">Try searching:</span>
          <div className="sample-chips">
            {sampleQueries.map((sq, idx) => (
              <button
                key={idx}
                type="button"
                className="sample-chip font-mono"
                onClick={() => {
                  setQuery(sq);
                }}
              >
                &ldquo;{sq}&rdquo;
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Search Error State */}
      {searchError && (
        <div className="indexing-error-banner glass-card animate-fade-in" id="search-error-card">
          <div className="alert-icon text-error">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <div>
            <h4 style={{ margin: 0, color: '#f87171' }}>Search Failed</h4>
            <p className="font-mono text-sm text-error" style={{ margin: '4px 0 0 0' }}>{searchError}</p>
            {searchError.includes('Vector index not found') && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                style={{ marginTop: '10px' }}
                onClick={triggerBuildIndex}
              >
                Enable Code Search Now
              </button>
            )}
          </div>
        </div>
      )}

      {/* Searching Loading State */}
      {searching && (
        <div className="glass-card search-loading-card animate-fade-in" id="search-loading-state">
          <div className="loading-spinner-lg"></div>
          <h3 className="search-state-title">Searching code...</h3>
          <p className="text-secondary font-mono text-sm">
            Finding relevant code sections in your project...
          </p>
        </div>
      )}

      {/* Search Empty State */}
      {hasSearched && !searching && !searchError && searchResults && searchResults.results?.length === 0 && (
        <div className="glass-card search-empty-card animate-fade-in" id="search-empty-state">
          <div className="empty-icon-wrap">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              <line x1="8" y1="11" x2="14" y2="11"></line>
            </svg>
          </div>
          <h3 className="search-state-title">No relevant code found</h3>
          <p className="text-secondary font-mono text-sm">
            Try a different natural-language query or search keywords related to functions, symbols, or libraries.
          </p>
        </div>
      )}

      {/* Search Results Display */}
      {!searching && searchResults && searchResults.results?.length > 0 && (
        <section className="search-results-section animate-fade-in" id="search-results-list">
          <div className="results-header-row">
            <h2 className="results-heading font-mono">
              Found {searchResults.results.length} Relevant Code Results
            </h2>
            <span className="results-query-summary font-mono text-xs text-secondary">
              Query: &ldquo;{searchResults.query}&rdquo;
            </span>
          </div>

          <div className="results-list">
            {searchResults.results.map((result, idx) => {
              const meta = result.metadata || {};
              const scorePercent = (result.score * 100).toFixed(1);
              const isVeryHigh = result.score >= 0.7;
              const isMedium = result.score >= 0.4;

              return (
                <div
                  key={result.chunk_id || idx}
                  className="search-result-card glass-card"
                  id={`search-result-${idx}`}
                >
                  <div className="result-card-header">
                    <div className="result-card-left">
                      <span className="result-rank font-mono">#{idx + 1}</span>
                      <div className="result-file-info">
                        <div className="result-file-name font-mono font-bold">
                          {meta.file_name || meta.file_path?.split('/').pop() || 'file'}
                        </div>
                        <div className="result-file-path font-mono text-xs text-secondary">
                          {meta.file_path}
                        </div>
                      </div>
                    </div>

                    <div className="result-card-right">
                      {meta.language && (
                        <span className="badge badge-purple font-mono text-xs">
                          {meta.language}
                        </span>
                      )}
                      {meta.symbol_type && (
                        <span className="badge badge-cyan font-mono text-xs">
                          {meta.symbol_type}: {meta.symbol_name || 'anonymous'}
                        </span>
                      )}
                      <span
                        className={`result-score-pill font-mono text-xs ${
                          isVeryHigh ? 'score-high' : isMedium ? 'score-medium' : 'score-low'
                        }`}
                        title="Relevance match"
                      >
                        {isVeryHigh ? 'High Match' : isMedium ? 'Good Match' : 'Match'} ({scorePercent}%)
                      </span>
                    </div>
                  </div>

                  <div className="result-meta-bar font-mono text-xs text-secondary">
                    <span>Lines {meta.start_line} &ndash; {meta.end_line}</span>
                    {meta.parent_symbol && (
                      <span>&bull; Scope: <code>{meta.parent_symbol}</code></span>
                    )}
                    <span style={{ marginLeft: 'auto' }}>
                      <Link
                        to={`/dashboard/projects/${projectId}/explorer?file=${encodeURIComponent(meta.file_path)}`}
                        className="view-in-explorer-link"
                        title="View file in File Explorer"
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="15 3 21 3 21 9"></polyline>
                          <polyline points="9 21 3 21 3 15"></polyline>
                          <line x1="21" y1="3" x2="14" y2="10"></line>
                          <line x1="3" y1="21" x2="10" y2="14"></line>
                        </svg>
                        <span>Open in Explorer</span>
                      </Link>
                    </span>
                  </div>

                  {/* Code Preview */}
                  <div className="result-code-preview">
                    <pre className="code-block font-mono">
                      <code>{result.content}</code>
                    </pre>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

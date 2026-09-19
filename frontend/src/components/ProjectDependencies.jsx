import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProjectDependencies() {
  const { projectId } = useParams();
  const { token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();

  const [depData, setDepData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter & Search states
  const [activeTab, setActiveTab] = useState('imports'); // 'imports' | 'packages' | 'relationships'
  const [importSearch, setImportSearch] = useState('');
  const [importTypeFilter, setImportTypeFilter] = useState('all'); // 'all' | 'local' | 'external' | 'unknown'
  const [packageEcoFilter, setPackageEcoFilter] = useState('all'); // 'all' | 'python' | 'javascript' | 'java'
  const [relTypeFilter, setRelTypeFilter] = useState('all'); // 'all' | 'local' | 'external'

  // Fetch Dependencies API
  const fetchDependencies = useCallback(async () => {
    if (!token || !projectId) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/dependencies`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || `Failed to fetch project dependencies (HTTP ${res.status})`);
      }

      setDepData(data);
      localStorage.setItem('codesage_active_project', String(projectId));
      if (data.project_name) {
        localStorage.setItem('codesage_active_project_name', data.project_name);
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred while analyzing project dependencies.');
    } finally {
      setLoading(false);
    }
  }, [BACKEND_URL, projectId, token, logout, navigate]);

  useEffect(() => {
    fetchDependencies();
  }, [fetchDependencies]);

  // Loading State (Phase 23)
  if (loading) {
    return (
      <div className="explorer-loading-state glass-card" id="dependencies-loading-state">
        <div className="loading-spinner"></div>
        <h3>Analyzing dependencies...</h3>
        <p className="text-secondary font-mono">
          Detecting source imports, resolving local files, and reading package manifests
        </p>
      </div>
    );
  }

  // Error State (Phase 24)
  if (error) {
    return (
      <div className="explorer-error-state glass-card" id="dependencies-error-state">
        <div className="error-icon-box">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
        <h2>Dependency Analysis Error</h2>
        <p className="error-message">{error}</p>
        <div className="error-actions">
          <Link to="/dashboard/projects" className="btn btn-primary" id="error-return-projects-btn">
            Return to Projects
          </Link>
          <button type="button" className="btn btn-ghost" onClick={fetchDependencies} id="error-retry-btn">
            Retry Analysis
          </button>
        </div>
      </div>
    );
  }

  const { project_name, imports = [], packages = [], relationships = [], graph } = depData || {};

  // Compute Metrics
  const totalImports = imports.length;
  const localImportsCount = imports.filter((i) => i.type === 'local').length;
  const externalImportsCount = imports.filter((i) => i.type === 'external').length;
  const totalPackages = packages.length;
  const hasNoDependencies = totalImports === 0 && totalPackages === 0;

  // Filter Imports
  const filteredImports = imports.filter((item) => {
    const matchesType = importTypeFilter === 'all' || item.type === importTypeFilter;
    const query = importSearch.toLowerCase().trim();
    const matchesSearch =
      !query ||
      item.source.toLowerCase().includes(query) ||
      item.name.toLowerCase().includes(query) ||
      (item.target && item.target.toLowerCase().includes(query));
    return matchesType && matchesSearch;
  });

  // Filter Packages
  const filteredPackages = packages.filter((pkg) => {
    if (packageEcoFilter === 'all') return true;
    return pkg.ecosystem.toLowerCase() === packageEcoFilter.toLowerCase();
  });

  // Group Packages by Ecosystem
  const pythonPackages = filteredPackages.filter((p) => p.ecosystem === 'python');
  const jsPackages = filteredPackages.filter((p) => p.ecosystem === 'javascript');
  const javaPackages = filteredPackages.filter((p) => p.ecosystem === 'java');

  // Filter Relationships
  const filteredRelationships = relationships.filter((rel) => {
    if (relTypeFilter === 'all') return true;
    return rel.dependency_type === relTypeFilter;
  });

  return (
    <div className="project-analysis-container animate-fade-in" id="project-dependencies-view">
      {/* Header Card & Navigation */}
      <header className="analysis-header-card glass-card">
        <div className="analysis-header-left">
          <nav className="explorer-breadcrumbs font-mono" aria-label="Breadcrumb">
            <Link to="/dashboard" className="crumb-link">Dashboard</Link>
            <span className="crumb-sep">/</span>
            <Link to="/dashboard/projects" className="crumb-link">Projects</Link>
            <span className="crumb-sep">/</span>
            <span className="crumb-active">{project_name || 'Project'}</span>
            <span className="crumb-sep">/</span>
            <span className="crumb-tag font-mono">Dependencies</span>
          </nav>

          <div className="project-title-row">
            <div className="project-header-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="18" cy="5" r="3"></circle>
                <circle cx="6" cy="12" r="3"></circle>
                <circle cx="18" cy="19" r="3"></circle>
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
              </svg>
            </div>
            <div>
              <h1 className="analysis-project-title" id="dependencies-project-title">
                {project_name}
              </h1>
              <p className="analysis-project-sub text-secondary font-mono">
                Dependency Analysis &bull; Module relationships &bull; External packages
              </p>
            </div>
          </div>
        </div>

        <div className="analysis-header-right">
          {/* Refresh Analysis Button */}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={fetchDependencies}
            disabled={loading}
            id="refresh-dependencies-btn"
            title="Re-run dependency analysis"
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
              className={loading ? 'animate-spin' : ''}
            >
              <path d="M23 4v6h-6"></path>
              <path d="M1 20v-6h6"></path>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            <span>Refresh Analysis</span>
          </button>

          {/* Link to Overview */}
          <Link
            to={`/dashboard/projects/${projectId}`}
            className="btn btn-secondary btn-sm"
            id="view-overview-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
            <span>Overview</span>
          </Link>

          {/* Link to Code Explorer */}
          <Link
            to={`/dashboard/projects/${projectId}/explorer`}
            className="btn btn-secondary btn-sm"
            id="explore-code-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"></polyline>
              <polyline points="8 6 2 12 8 18"></polyline>
            </svg>
            <span>Explore Code</span>
          </Link>

          {/* Day 12: Semantic Search Link */}
          <Link
            to={`/dashboard/projects/${projectId}/search`}
            className="btn btn-primary btn-sm"
            id="search-code-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <span>Search Code</span>
          </Link>
        </div>
      </header>

      {/* Empty State Banner (Phase 25) */}
      {hasNoDependencies && (
        <div className="empty-project-alert glass-card" id="empty-dependencies-notice">
          <div className="alert-icon text-warning">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <div>
            <h4 className="alert-title">No dependencies detected</h4>
            <p className="alert-desc text-secondary">
              No imports or package manifests (e.g. requirements.txt, package.json, pom.xml) were found in this project.
            </p>
          </div>
        </div>
      )}

      {/* Key Metric Strip */}
      <section className="analysis-metrics-grid" aria-label="Dependency Metrics">
        <div className="metric-card glass-card" id="metric-total-imports">
          <div className="metric-header">
            <span className="metric-title text-secondary">Total Imports</span>
            <div className="metric-icon metric-icon-primary">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <polyline points="19 12 12 19 5 12"></polyline>
              </svg>
            </div>
          </div>
          <div className="metric-value font-mono">{totalImports}</div>
          <div className="metric-subtext text-secondary">Detected in source files</div>
        </div>

        <div className="metric-card glass-card" id="metric-local-deps">
          <div className="metric-header">
            <span className="metric-title text-secondary">Local Dependencies</span>
            <div className="metric-icon metric-icon-success">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
              </svg>
            </div>
          </div>
          <div className="metric-value font-mono text-success">{localImportsCount}</div>
          <div className="metric-subtext text-secondary">Resolved internal modules</div>
        </div>

        <div className="metric-card glass-card" id="metric-external-deps">
          <div className="metric-header">
            <span className="metric-title text-secondary">External Dependencies</span>
            <div className="metric-icon metric-icon-info">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                <line x1="12" y1="22.08" x2="12" y2="12"></line>
              </svg>
            </div>
          </div>
          <div className="metric-value font-mono text-info">{externalImportsCount}</div>
          <div className="metric-subtext text-secondary">Third-party / standard libraries</div>
        </div>

        <div className="metric-card glass-card" id="metric-declared-packages">
          <div className="metric-header">
            <span className="metric-title text-secondary">Declared Packages</span>
            <div className="metric-icon metric-icon-purple">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 12 20 22 4 22 4 12"></polyline>
                <rect x="2" y="7" width="20" height="5"></rect>
                <line x1="12" y1="22" x2="12" y2="7"></line>
              </svg>
            </div>
          </div>
          <div className="metric-value font-mono text-purple">{totalPackages}</div>
          <div className="metric-subtext text-secondary">From dependency manifests</div>
        </div>
      </section>

      {/* Main Tab Navigation */}
      <div className="dep-tabs-container glass-card">
        <div className="dep-tab-buttons">
          <button
            type="button"
            className={`dep-tab-btn ${activeTab === 'imports' ? 'active' : ''}`}
            onClick={() => setActiveTab('imports')}
            id="tab-imports-btn"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="8" y1="6" x2="21" y2="6"></line>
              <line x1="8" y1="12" x2="21" y2="12"></line>
              <line x1="8" y1="18" x2="21" y2="18"></line>
              <line x1="3" y1="6" x2="3.01" y2="6"></line>
              <line x1="3" y1="12" x2="3.01" y2="12"></line>
              <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
            <span>Imports</span>
            <span className="dep-tab-badge font-mono">{totalImports}</span>
          </button>

          <button
            type="button"
            className={`dep-tab-btn ${activeTab === 'packages' ? 'active' : ''}`}
            onClick={() => setActiveTab('packages')}
            id="tab-packages-btn"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            </svg>
            <span>Packages</span>
            <span className="dep-tab-badge font-mono">{totalPackages}</span>
          </button>

          <button
            type="button"
            className={`dep-tab-btn ${activeTab === 'relationships' ? 'active' : ''}`}
            onClick={() => setActiveTab('relationships')}
            id="tab-relationships-btn"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3"></circle>
              <circle cx="6" cy="12" r="3"></circle>
              <circle cx="18" cy="19" r="3"></circle>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
            </svg>
            <span>Relationships</span>
            <span className="dep-tab-badge font-mono">{relationships.length}</span>
          </button>
        </div>
      </div>

      {/* -------------------------------------------------------------------- */}
      {/* TAB 1: IMPORTS (Phases 19) */}
      {/* -------------------------------------------------------------------- */}
      {activeTab === 'imports' && (
        <div className="dep-tab-content glass-card animate-fade-in" id="tab-imports-content">
          <div className="dep-table-toolbar">
            <div className="dep-search-box">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
              <input
                type="text"
                className="dep-search-input"
                placeholder="Search file or import name..."
                value={importSearch}
                onChange={(e) => setImportSearch(e.target.value)}
                id="imports-search-input"
              />
              {importSearch && (
                <button
                  type="button"
                  className="dep-clear-btn"
                  onClick={() => setImportSearch('')}
                  title="Clear search"
                >
                  &times;
                </button>
              )}
            </div>

            <div className="dep-filter-group">
              <span className="dep-filter-label text-secondary">Filter:</span>
              <button
                type="button"
                className={`dep-filter-chip ${importTypeFilter === 'all' ? 'active' : ''}`}
                onClick={() => setImportTypeFilter('all')}
              >
                All ({totalImports})
              </button>
              <button
                type="button"
                className={`dep-filter-chip chip-success ${importTypeFilter === 'local' ? 'active' : ''}`}
                onClick={() => setImportTypeFilter('local')}
              >
                Local ({localImportsCount})
              </button>
              <button
                type="button"
                className={`dep-filter-chip chip-info ${importTypeFilter === 'external' ? 'active' : ''}`}
                onClick={() => setImportTypeFilter('external')}
              >
                External ({externalImportsCount})
              </button>
              <button
                type="button"
                className={`dep-filter-chip chip-unknown ${importTypeFilter === 'unknown' ? 'active' : ''}`}
                onClick={() => setImportTypeFilter('unknown')}
              >
                Unknown ({totalImports - localImportsCount - externalImportsCount})
              </button>
            </div>
          </div>

          {filteredImports.length === 0 ? (
            <div className="dep-empty-table text-secondary font-mono">
              No imports matching current filter criteria.
            </div>
          ) : (
            <div className="dep-table-wrapper">
              <table className="dep-table" id="imports-table">
                <thead>
                  <tr>
                    <th>Source File</th>
                    <th>Imported Module / Symbol</th>
                    <th>Type</th>
                    <th>Resolved Target</th>
                    <th>Line</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredImports.map((imp, idx) => (
                    <tr key={`${imp.source}-${imp.name}-${idx}`} className="dep-table-row">
                      <td className="font-mono text-primary dep-file-cell">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2 inline text-secondary">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        <span>{imp.source}</span>
                      </td>
                      <td className="font-mono font-bold text-accent">
                        <code>{imp.name}</code>
                      </td>
                      <td>
                        <span className={`dep-badge badge-${imp.type}`}>
                          {imp.type.toUpperCase()}
                        </span>
                      </td>
                      <td className="font-mono text-secondary">
                        {imp.target ? (
                          <span className={imp.type === 'local' ? 'text-success' : 'text-info'}>
                            {imp.target}
                          </span>
                        ) : (
                          <span className="text-muted italic">Unresolved</span>
                        )}
                      </td>
                      <td className="font-mono text-muted">
                        {imp.line ? `L${imp.line}` : '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* -------------------------------------------------------------------- */}
      {/* TAB 2: PACKAGES (Phase 20) */}
      {/* -------------------------------------------------------------------- */}
      {activeTab === 'packages' && (
        <div className="dep-tab-content glass-card animate-fade-in" id="tab-packages-content">
          <div className="dep-table-toolbar">
            <div className="dep-filter-group">
              <span className="dep-filter-label text-secondary">Ecosystem:</span>
              <button
                type="button"
                className={`dep-filter-chip ${packageEcoFilter === 'all' ? 'active' : ''}`}
                onClick={() => setPackageEcoFilter('all')}
              >
                All ({packages.length})
              </button>
              <button
                type="button"
                className={`dep-filter-chip ${packageEcoFilter === 'python' ? 'active' : ''}`}
                onClick={() => setPackageEcoFilter('python')}
              >
                Python ({packages.filter((p) => p.ecosystem === 'python').length})
              </button>
              <button
                type="button"
                className={`dep-filter-chip ${packageEcoFilter === 'javascript' ? 'active' : ''}`}
                onClick={() => setPackageEcoFilter('javascript')}
              >
                JavaScript ({packages.filter((p) => p.ecosystem === 'javascript').length})
              </button>
              <button
                type="button"
                className={`dep-filter-chip ${packageEcoFilter === 'java' ? 'active' : ''}`}
                onClick={() => setPackageEcoFilter('java')}
              >
                Java ({packages.filter((p) => p.ecosystem === 'java').length})
              </button>
            </div>
          </div>

          {filteredPackages.length === 0 ? (
            <div className="dep-empty-table text-secondary font-mono">
              No declared packages found in project dependency manifests.
            </div>
          ) : (
            <div className="dep-ecosystems-grid">
              {/* Python Ecosystem */}
              {pythonPackages.length > 0 && (
                <div className="dep-eco-section">
                  <div className="dep-eco-header">
                    <div className="dep-eco-icon text-cyan">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="4 17 10 11 4 5"></polyline>
                        <line x1="12" y1="19" x2="20" y2="19"></line>
                      </svg>
                    </div>
                    <h3 className="dep-eco-title">Python Dependencies</h3>
                    <span className="dep-badge font-mono">{pythonPackages.length}</span>
                  </div>

                  <div className="dep-package-cards">
                    {pythonPackages.map((pkg, idx) => (
                      <div key={`py-${pkg.name}-${idx}`} className="dep-package-card glass-subcard">
                        <div className="dep-pkg-top">
                          <span className="dep-pkg-name font-mono">{pkg.name}</span>
                          <span className={`dep-badge badge-${pkg.type}`}>
                            {pkg.type}
                          </span>
                        </div>
                        <div className="dep-pkg-meta font-mono">
                          <span className="dep-pkg-ver text-secondary">
                            {pkg.version ? `Version: ${pkg.version}` : 'Version: Not specified'}
                          </span>
                          {pkg.source && (
                            <span className="dep-pkg-source text-muted">
                              &bull; {pkg.source}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* JavaScript Ecosystem */}
              {jsPackages.length > 0 && (
                <div className="dep-eco-section">
                  <div className="dep-eco-header">
                    <div className="dep-eco-icon text-warning">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="2" width="20" height="20" rx="4"></rect>
                        <path d="M10 16V8"></path>
                        <path d="M14 12c.5-1 1.5-1.5 2.5-1 1 .5 1.5 1.5 1 2.5-.5 1-2 1.5-3 1.5"></path>
                      </svg>
                    </div>
                    <h3 className="dep-eco-title">JavaScript Dependencies</h3>
                    <span className="dep-badge font-mono">{jsPackages.length}</span>
                  </div>

                  <div className="dep-package-cards">
                    {jsPackages.map((pkg, idx) => (
                      <div key={`js-${pkg.name}-${idx}`} className="dep-package-card glass-subcard">
                        <div className="dep-pkg-top">
                          <span className="dep-pkg-name font-mono">{pkg.name}</span>
                          <span className={`dep-badge badge-${pkg.type}`}>
                            {pkg.type}
                          </span>
                        </div>
                        <div className="dep-pkg-meta font-mono">
                          <span className="dep-pkg-ver text-secondary">
                            {pkg.version ? `Version: ${pkg.version}` : 'Version: Not specified'}
                          </span>
                          {pkg.source && (
                            <span className="dep-pkg-source text-muted">
                              &bull; {pkg.source}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Java Ecosystem */}
              {javaPackages.length > 0 && (
                <div className="dep-eco-section">
                  <div className="dep-eco-header">
                    <div className="dep-eco-icon text-orange">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M18 8h1a4 4 0 0 1 0 8h-1"></path>
                        <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path>
                        <line x1="6" y1="1" x2="6" y2="4"></line>
                        <line x1="10" y1="1" x2="10" y2="4"></line>
                        <line x1="14" y1="1" x2="14" y2="4"></line>
                      </svg>
                    </div>
                    <h3 className="dep-eco-title">Java Dependencies</h3>
                    <span className="dep-badge font-mono">{javaPackages.length}</span>
                  </div>

                  <div className="dep-package-cards">
                    {javaPackages.map((pkg, idx) => (
                      <div key={`java-${pkg.name}-${idx}`} className="dep-package-card glass-subcard">
                        <div className="dep-pkg-top">
                          <span className="dep-pkg-name font-mono">{pkg.name}</span>
                          <span className={`dep-badge badge-${pkg.type}`}>
                            {pkg.type}
                          </span>
                        </div>
                        <div className="dep-pkg-meta font-mono">
                          <span className="dep-pkg-ver text-secondary">
                            {pkg.version ? `Version: ${pkg.version}` : 'Version: Not specified'}
                          </span>
                          {pkg.source && (
                            <span className="dep-pkg-source text-muted">
                              &bull; {pkg.source}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* -------------------------------------------------------------------- */}
      {/* TAB 3: RELATIONSHIPS & GRAPH (Phases 21-22) */}
      {/* -------------------------------------------------------------------- */}
      {activeTab === 'relationships' && (
        <div className="dep-tab-content glass-card animate-fade-in" id="tab-relationships-content">
          <div className="dep-table-toolbar">
            <div className="dep-filter-group">
              <span className="dep-filter-label text-secondary">Filter Relationships:</span>
              <button
                type="button"
                className={`dep-filter-chip ${relTypeFilter === 'all' ? 'active' : ''}`}
                onClick={() => setRelTypeFilter('all')}
              >
                All ({relationships.length})
              </button>
              <button
                type="button"
                className={`dep-filter-chip chip-success ${relTypeFilter === 'local' ? 'active' : ''}`}
                onClick={() => setRelTypeFilter('local')}
              >
                Internal Imports ({relationships.filter((r) => r.dependency_type === 'local').length})
              </button>
              <button
                type="button"
                className={`dep-filter-chip chip-info ${relTypeFilter === 'external' ? 'active' : ''}`}
                onClick={() => setRelTypeFilter('external')}
              >
                External Depends ({relationships.filter((r) => r.dependency_type === 'external').length})
              </button>
            </div>

            {graph && (
              <div className="dep-graph-stats font-mono text-secondary">
                <span>Nodes: <strong>{graph.nodes?.length || 0}</strong></span>
                <span className="mx-2">&bull;</span>
                <span>Edges: <strong>{graph.edges?.length || 0}</strong></span>
              </div>
            )}
          </div>

          {filteredRelationships.length === 0 ? (
            <div className="dep-empty-table text-secondary font-mono">
              No dependency relationships found matching filter.
            </div>
          ) : (
            <div className="dep-relationships-list" id="relationships-list">
              {filteredRelationships.map((rel, idx) => (
                <div
                  key={`${rel.source}-${rel.target}-${idx}`}
                  className="dep-rel-card glass-subcard animate-fade-in"
                >
                  {/* Source Node */}
                  <div className="dep-rel-node source-node">
                    <div className="dep-node-badge file-badge">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                      </svg>
                      <span>FILE</span>
                    </div>
                    <span className="dep-node-name font-mono" title={rel.source}>
                      {rel.source}
                    </span>
                  </div>

                  {/* Relationship Flow Arrow */}
                  <div className="dep-rel-connector">
                    <span className={`dep-rel-type-pill pill-${rel.dependency_type || 'local'}`}>
                      {rel.type === 'imports' ? 'imports' : 'depends on'}
                    </span>
                    <div className="dep-rel-arrow-line">
                      <svg width="24" height="14" viewBox="0 0 24 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="0" y1="7" x2="20" y2="7"></line>
                        <polyline points="15 2 20 7 15 12"></polyline>
                      </svg>
                    </div>
                  </div>

                  {/* Target Node */}
                  <div className={`dep-rel-node target-node ${rel.dependency_type === 'local' ? 'target-local' : 'target-external'}`}>
                    <div className={`dep-node-badge ${rel.dependency_type === 'local' ? 'file-badge' : 'package-badge'}`}>
                      {rel.dependency_type === 'local' ? (
                        <>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                          </svg>
                          <span>LOCAL FILE</span>
                        </>
                      ) : (
                        <>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                          </svg>
                          <span>PACKAGE</span>
                        </>
                      )}
                    </div>
                    <span className="dep-node-name font-mono" title={rel.target}>
                      {rel.target}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingState from './common/LoadingState';

export default function ProjectAnalysis() {
  const { projectId } = useParams();
  const { token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();

  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');

  // Day 10 Code Indexing States
  const [indexing, setIndexing] = useState(false);
  const [indexingStatus, setIndexingStatus] = useState(null);
  const [indexResult, setIndexResult] = useState(null);
  const [indexError, setIndexError] = useState(null);

  // Day 11 Embedding Generation States
  const [generatingEmbeddings, setGeneratingEmbeddings] = useState(false);
  const [embeddingStatus, setEmbeddingStatus] = useState(null);
  const [embeddingResult, setEmbeddingResult] = useState(null);
  const [embeddingError, setEmbeddingError] = useState(null);

  // Day 12 FAISS Vector Index States
  const [buildingVectorIndex, setBuildingVectorIndex] = useState(false);
  const [vectorIndexStatus, setVectorIndexStatus] = useState(null);
  const [vectorIndexResult, setVectorIndexResult] = useState(null);
  const [vectorIndexError, setVectorIndexError] = useState(null);

  // Day 22 Export States
  const [exportingMd, setExportingMd] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportNotification, setExportNotification] = useState(null);
  const [exportError, setExportError] = useState(null);

  // Helper to format sizes nicely
  const formatSize = (bytes) => {
    if (!bytes && bytes !== 0) return '--';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Color mapping for common languages
  const getLanguageColor = (lang) => {
    const colors = {
      Python: '#38bdf8',
      JavaScript: '#facc15',
      TypeScript: '#60a5fa',
      Java: '#f97316',
      HTML: '#ea580c',
      CSS: '#a855f7',
      SCSS: '#ec4899',
      JSON: '#94a3b8',
      YAML: '#fb7185',
      Markdown: '#34d399',
      SQL: '#38bdf8',
      Go: '#00add8',
      Rust: '#f97316',
      'C++': '#f43f5e',
      C: '#64748b',
      'C/C++': '#f43f5e',
      'C#': '#a855f7',
      PHP: '#818cf8',
      Ruby: '#ef4444',
      Shell: '#10b981',
    };
    return colors[lang] || '#94a3b8';
  };

  // Fetch Project Analysis API
  const fetchAnalysis = useCallback(async () => {
    if (!token || !projectId) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/analysis`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to retrieve project analysis.');
      }

      setAnalysisData(data);

      // Track active project across dashboard and sidebar
      localStorage.setItem('codesage_active_project', String(projectId));
      if (data.project_name) {
        localStorage.setItem('codesage_active_project_name', data.project_name);
      }
      const initialExpanded = new Set();
      if (data.folder_hierarchy && data.folder_hierarchy.children) {
        data.folder_hierarchy.children.forEach((child) => {
          if (child.type === 'folder') {
            initialExpanded.add(child.path || child.name);
          }
        });
      }
      setExpandedFolders(initialExpanded);
    } catch (err) {
      setError(err.message || 'Failed to analyze project.');
      setAnalysisData(null);
    } finally {
      setLoading(false);
    }
  }, [BACKEND_URL, projectId, token, logout, navigate]);

  // Day 10: Fetch current code indexing status
  const fetchIndexStatus = useCallback(async () => {
    if (!token || !projectId) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/index/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setIndexingStatus(data);
      }
    } catch {
      // ignore background status failures
    }
  }, [BACKEND_URL, projectId, token]);

  // Day 10: Trigger Code Indexing pipeline
  const triggerIndexing = async () => {
    if (!token || !projectId || indexing) return;
    setIndexing(true);
    setIndexError(null);
    setIndexResult(null);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/index`, {
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
        throw new Error(data.detail || 'Failed to index project source code.');
      }

      setIndexResult(data);
      fetchIndexStatus();
      fetchEmbeddingStatus();
    } catch (err) {
      setIndexError(err.message || 'An unexpected error occurred during indexing.');
    } finally {
      setIndexing(false);
    }
  };

  // Day 11: Fetch current embedding status
  const fetchEmbeddingStatus = useCallback(async () => {
    if (!token || !projectId) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/embeddings/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setEmbeddingStatus(data);
      }
    } catch {
      // ignore background status failures
    }
  }, [BACKEND_URL, projectId, token]);

  // Day 11: Trigger Embedding Generation pipeline
  const triggerEmbeddingGeneration = async () => {
    if (!token || !projectId || generatingEmbeddings) return;

    // Ensure project has indexed chunks (Phase 24 & 28)
    if (indexingStatus?.status !== 'indexed' || (indexingStatus?.total_chunks || 0) === 0) {
      setEmbeddingError('Please analyze the project code before preparing for AI.');
      return;
    }

    setGeneratingEmbeddings(true);
    setEmbeddingError(null);
    setEmbeddingResult(null);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/embeddings`, {
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
        throw new Error(data.detail || 'Failed to prepare project for AI.');
      }

      setEmbeddingResult(data);
      fetchEmbeddingStatus();
      fetchVectorIndexStatus();
    } catch (err) {
      setEmbeddingError(err.message || 'An unexpected error occurred while preparing the project for AI.');
    } finally {
      setGeneratingEmbeddings(false);
    }
  };

  // Day 12: Fetch current vector index status
  const fetchVectorIndexStatus = useCallback(async () => {
    if (!token || !projectId) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/vector-index/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setVectorIndexStatus(data);
      }
    } catch {
      // ignore background status failures
    }
  }, [BACKEND_URL, projectId, token]);

  // Day 12: Trigger Vector Index Build
  const triggerVectorIndexBuild = async () => {
    if (!token || !projectId || buildingVectorIndex) return;

    if (embeddingStatus?.status !== 'ready' && (embeddingStatus?.embedded_chunks || 0) === 0) {
      setVectorIndexError('Please prepare the project for AI before enabling code search.');
      return;
    }

    setBuildingVectorIndex(true);
    setVectorIndexError(null);
    setVectorIndexResult(null);

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

      setVectorIndexResult(data);
      fetchVectorIndexStatus();
    } catch (err) {
      setVectorIndexError(err.message || 'An unexpected error occurred during index build.');
    } finally {
      setBuildingVectorIndex(false);
    }
  };

  // Day 22: Helper to trigger browser file download from Blob
  const downloadBlob = (blob, defaultFilename) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = defaultFilename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  // Day 22: Export Project Technical Report as Markdown
  const handleExportMarkdown = async () => {
    if (!token || !projectId || exportingMd) return;
    setExportingMd(true);
    setExportError(null);
    setExportNotification(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/export/markdown`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to export Markdown report.');
      }
      const cd = res.headers.get('Content-Disposition');
      let filename = `${analysisData?.project_name || 'Project'}_Report.md`;
      if (cd) {
        const match = cd.match(/filename="?([^";]+)"?/);
        if (match && match[1]) filename = match[1];
      }
      const blob = await res.blob();
      downloadBlob(blob, filename);
      setExportNotification(`Downloaded ${filename}`);
      setTimeout(() => setExportNotification(null), 4000);
    } catch (err) {
      setExportError(err.message || 'Error exporting Markdown report.');
    } finally {
      setExportingMd(false);
    }
  };

  // Day 22: Export Project Technical Report as PDF
  const handleExportPdf = async () => {
    if (!token || !projectId || exportingPdf) return;
    setExportingPdf(true);
    setExportError(null);
    setExportNotification(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/export/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to export PDF report.');
      }
      const cd = res.headers.get('Content-Disposition');
      let filename = `${analysisData?.project_name || 'Project'}_Report.pdf`;
      if (cd) {
        const match = cd.match(/filename="?([^";]+)"?/);
        if (match && match[1]) filename = match[1];
      }
      const blob = await res.blob();
      downloadBlob(blob, filename);
      setExportNotification(`Downloaded ${filename}`);
      setTimeout(() => setExportNotification(null), 4000);
    } catch (err) {
      setExportError(err.message || 'Error exporting PDF report.');
    } finally {
      setExportingPdf(false);
    }
  };

  useEffect(() => {
    fetchAnalysis();
    fetchIndexStatus();
    fetchEmbeddingStatus();
    fetchVectorIndexStatus();
  }, [fetchAnalysis, fetchIndexStatus, fetchEmbeddingStatus, fetchVectorIndexStatus]);

  // Toggle folder expansion
  const toggleFolder = (folderPath) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderPath)) {
        next.delete(folderPath);
      } else {
        next.add(folderPath);
      }
      return next;
    });
  };

  // Recursive Tree Node Renderer for Folder Hierarchy
  const renderTreeNode = (node, depth = 0) => {
    const isFolder = node.type === 'folder';
    const nodeKey = node.path || node.name;
    const isExpanded = expandedFolders.has(nodeKey);

    // Filter matching
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchesSelf = node.name.toLowerCase().includes(q);
      const matchesChildren = (nodes) =>
        nodes.some(
          (c) =>
            c.name.toLowerCase().includes(q) ||
            (c.type === 'folder' && c.children && matchesChildren(c.children))
        );

      if (isFolder && !matchesSelf && (!node.children || !matchesChildren(node.children))) {
        return null;
      }
      if (!isFolder && !matchesSelf) {
        return null;
      }
    }

    const paddingLeft = `${depth * 14 + 10}px`;

    if (isFolder) {
      return (
        <div key={nodeKey} className="tree-folder-group">
          <div
            className={`tree-node folder-node ${isExpanded ? 'expanded' : ''}`}
            style={{ paddingLeft }}
            onClick={() => toggleFolder(nodeKey)}
            title={node.path || node.name}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && toggleFolder(nodeKey)}
          >
            <span className="folder-arrow">{isExpanded ? '▾' : '▸'}</span>
            <svg
              className="tree-icon folder-icon"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
            <span className="node-name folder-name">{node.name}</span>
          </div>

          {isExpanded && node.children && (
            <div className="folder-children">
              {node.children.length === 0 ? (
                <div className="empty-folder-hint" style={{ paddingLeft: `${(depth + 1) * 14 + 10}px` }}>
                  (empty)
                </div>
              ) : (
                node.children.map((child) => renderTreeNode(child, depth + 1))
              )}
            </div>
          )}
        </div>
      );
    }

    // File Node
    return (
      <div
        key={nodeKey}
        className="tree-node file-node"
        style={{ paddingLeft }}
        title={node.path}
      >
        <svg
          className="tree-icon file-icon"
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
        </svg>
        <span className="node-name file-name">{node.name}</span>
        {node.size !== undefined && node.size !== null && (
          <span className="node-size-pill font-mono">{formatSize(node.size)}</span>
        )}
      </div>
    );
  };

  // Loading State (Phase 20)
  if (loading) {
    return (
      <LoadingState
        title="Analyzing project..."
        message="Generating structure, language breakdown, and statistics"
        id="analysis-loading-state"
      />
    );
  }

  // Error State (Phase 21)
  if (error) {
    return (
      <div className="explorer-error-state glass-card" id="analysis-error-state">
        <div className="error-icon-box">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
        <h2>Project Analysis Error</h2>
        <p className="error-message">{error}</p>
        <div className="error-actions">
          <Link to="/dashboard/projects" className="btn btn-primary" id="error-return-projects-btn">
            Return to Projects
          </Link>
          <button type="button" className="btn btn-ghost" onClick={fetchAnalysis} id="error-retry-btn">
            Retry Analysis
          </button>
        </div>
      </div>
    );
  }

  const { statistics, languages, file_count, folder_hierarchy, project_name } = analysisData || {};
  const totalFiles = statistics?.total_files || 0;
  const totalFolders = statistics?.total_folders || 0;
  const totalSizeFormatted = statistics?.total_size_mb >= 1
    ? `${statistics.total_size_mb} MB`
    : `${statistics?.total_size_kb || 0} KB`;
  const languageList = Object.entries(languages || {});
  const extensionList = Object.entries(file_count?.by_extension || {});

  return (
    <div className="project-analysis-container animate-fade-in" id="project-analysis-view">
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
            <span className="crumb-tag font-mono">Overview</span>
          </nav>

          <div className="project-title-row">
            <div className="project-header-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
            </div>
            <div>
              <h1 className="analysis-project-title" id="analysis-project-title">{project_name}</h1>
              <p className="analysis-project-sub text-secondary font-mono">
                Project Overview &bull; Structure, languages, code metrics, and dependencies
              </p>
            </div>
          </div>
        </div>

        <div className="analysis-header-right">
          {/* Refresh Analysis Button (Phase 23) */}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={fetchAnalysis}
            disabled={loading}
            id="refresh-analysis-btn"
            title="Re-run project diagnostics"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={loading ? 'animate-spin' : ''}>
              <path d="M23 4v6h-6"></path>
              <path d="M1 20v-6h6"></path>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            <span>Refresh Analysis</span>
          </button>

          {/* Analyze Code Action */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={triggerIndexing}
            disabled={indexing || loading}
            id="index-project-btn"
            title="Analyze project code structure and symbols"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={indexing ? 'animate-spin' : ''}
            >
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span>{indexing ? 'Analyzing code...' : (indexingStatus?.status === 'indexed' ? 'Re-analyze Code' : 'Analyze Code')}</span>
          </button>

          {/* Prepare Project for AI Action */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={triggerEmbeddingGeneration}
            disabled={generatingEmbeddings || loading || indexing || indexingStatus?.status !== 'indexed'}
            id="generate-embeddings-btn"
            title={
              indexingStatus?.status !== 'indexed'
                ? 'Analyze code first before preparing for AI'
                : 'Prepare project for natural-language code search and AI assistance'
            }
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={generatingEmbeddings ? 'animate-spin' : ''}
            >
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            <span>
              {generatingEmbeddings
                ? 'Preparing for AI...'
                : embeddingStatus?.status === 'ready'
                ? 'Refresh AI Readiness'
                : 'Prepare Project for AI'}
            </span>
          </button>

          {/* Dependencies Link */}
          <Link
            to={`/dashboard/projects/${projectId}/dependencies`}
            className="btn btn-secondary btn-sm"
            id="view-dependencies-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3"></circle>
              <circle cx="6" cy="12" r="3"></circle>
              <circle cx="18" cy="19" r="3"></circle>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
            </svg>
            <span>Dependencies</span>
          </Link>

          {/* Search Code Link */}
          <Link
            to={`/dashboard/projects/${projectId}/search`}
            className="btn btn-secondary btn-sm"
            id="search-code-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <span>Search Code</span>
          </Link>

          {/* Ask AI Link */}
          <Link
            to={`/dashboard/projects/${projectId}/chat`}
            className="btn btn-secondary btn-sm"
            id="chat-codesage-btn"
            style={{
              borderColor: 'rgba(168, 85, 247, 0.4)',
              color: '#c084fc',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>Ask AI</span>
          </Link>

          {/* Function Docs Link */}
          <Link
            to={`/dashboard/projects/${projectId}/functions`}
            className="btn btn-secondary btn-sm"
            id="functions-doc-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
            <span>Documentation</span>
          </Link>

          {/* Explore Code Link */}
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

          {/* Day 22: Export Markdown Action */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleExportMarkdown}
            disabled={exportingMd || loading}
            id="export-markdown-btn"
            title="Download full project technical documentation as Markdown (.md)"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={exportingMd ? 'animate-spin' : ''}
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span>{exportingMd ? 'Exporting MD...' : 'Export MD'}</span>
          </button>

          {/* Day 22: Export PDF Action */}
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleExportPdf}
            disabled={exportingPdf || loading}
            id="export-pdf-btn"
            title="Download publication-quality project technical report as PDF (.pdf)"
            style={{
              background: 'linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)',
              border: 'none',
              color: '#030712',
              fontWeight: 600,
            }}
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={exportingPdf ? 'animate-spin' : ''}
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="12" y1="18" x2="12" y2="12"></line>
              <line x1="9" y1="15" x2="15" y2="15"></line>
            </svg>
            <span>{exportingPdf ? 'Generating PDF...' : 'Export PDF'}</span>
          </button>
        </div>
      </header>

      {/* Day 22: Export Notification / Feedback */}
      {exportNotification && (
        <div className="glass-card" style={{ padding: '0.75rem 1.25rem', marginBottom: '1.25rem', borderLeft: '4px solid #10b981', display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'rgba(16, 185, 129, 0.08)' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <span style={{ color: '#ecfdf5', fontSize: '0.9rem' }}>{exportNotification}</span>
        </div>
      )}
      {exportError && (
        <div className="glass-card" style={{ padding: '0.75rem 1.25rem', marginBottom: '1.25rem', borderLeft: '4px solid #ef4444', display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'rgba(239, 68, 68, 0.08)' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span style={{ color: '#fee2e2', fontSize: '0.9rem' }}>{exportError}</span>
        </div>
      )}

      {/* Empty Project Warning (Phase 22) */}
      {totalFiles === 0 && (
        <div className="empty-project-alert glass-card" id="empty-project-notice">
          <div className="alert-icon text-warning">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <div>
            <h4>No files found</h4>
            <p className="text-secondary">This project does not contain any files to analyze.</p>
          </div>
        </div>
      )}

      {/* Metric Cards Grid (Phase 16) */}
      <section className="analysis-metrics-grid" id="project-stats-grid">
        <div className="metric-card glass-card" id="metric-total-files">
          <div className="metric-icon-wrap cyan">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
          </div>
          <div className="metric-content">
            <span className="metric-label">Total Files</span>
            <span className="metric-value font-mono" id="stat-total-files">{totalFiles}</span>
          </div>
        </div>

        <div className="metric-card glass-card" id="metric-total-folders">
          <div className="metric-icon-wrap purple">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <div className="metric-content">
            <span className="metric-label">Total Folders</span>
            <span className="metric-value font-mono" id="stat-total-folders">{totalFolders}</span>
          </div>
        </div>

        <div className="metric-card glass-card" id="metric-project-size">
          <div className="metric-icon-wrap emerald">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
          </div>
          <div className="metric-content">
            <span className="metric-label">Project Size</span>
            <span className="metric-value font-mono" id="stat-project-size">{totalSizeFormatted}</span>
          </div>
        </div>

        <div className="metric-card glass-card" id="metric-languages-count">
          <div className="metric-icon-wrap amber">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"></polyline>
              <polyline points="8 6 2 12 8 18"></polyline>
            </svg>
          </div>
          <div className="metric-content">
            <span className="metric-label">Languages</span>
            <span className="metric-value font-mono" id="stat-languages-count">{languageList.length}</span>
          </div>
        </div>
      </section>

      {/* Code Analysis Card & Status */}
      <section className="indexing-pipeline-card glass-card animate-fade-in" id="indexing-section">
        <div className="indexing-card-header">
          <div className="indexing-title-wrap">
            <div className="indexing-icon-wrap">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </div>
            <div>
              <div className="indexing-title-row">
                <h3 className="indexing-title">Code Analysis Status</h3>
                {indexing ? (
                  <span className="badge badge-purple animate-pulse font-mono" id="indexing-badge-progress">
                    Analyzing code...
                  </span>
                ) : indexingStatus?.status === 'indexed' ? (
                  <span className="badge badge-success font-mono" id="indexing-badge-completed">
                    Analyzed ({indexingStatus.indexed_files} files)
                  </span>
                ) : (
                  <span className="badge badge-warning font-mono" id="indexing-badge-pending">
                    Not Analyzed
                  </span>
                )}
              </div>
              <p className="indexing-desc text-secondary font-mono">
                Introspects code structure, functions, classes, and project symbols
              </p>
            </div>
          </div>

          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={triggerIndexing}
            disabled={indexing || loading || totalFiles === 0}
            id="trigger-indexing-btn"
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
              className={indexing ? 'animate-spin' : ''}
            >
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span>{indexing ? 'Analyzing code...' : (indexingStatus?.status === 'indexed' ? 'Re-analyze Code' : 'Analyze Code')}</span>
          </button>
        </div>

        {/* Indexing Success Message */}
        {indexResult && (
          <div className="indexing-success-banner glass-subcard animate-fade-in" id="indexing-success-notice">
            <div className="alert-icon text-success">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </div>
            <div className="font-mono text-sm">
              <strong>Code analyzed successfully:</strong> {indexResult.indexed_files} source files processed and organized.
            </div>
          </div>
        )}

        {/* Indexing Error Message */}
        {indexError && (
          <div className="indexing-error-banner glass-subcard animate-fade-in" id="indexing-error-notice">
            <div className="alert-icon text-error">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </div>
            <div className="font-mono text-sm text-error">
              <strong>Analysis Error:</strong> {indexError}
            </div>
          </div>
        )}

        {/* Empty project warning */}
        {totalFiles === 0 && (
          <div className="indexing-empty-banner font-mono text-secondary text-sm">
            No analyzeable source files found in this project.
          </div>
        )}

        {/* Indexing Details Strip */}
        {indexingStatus?.status === 'indexed' && (
          <div className="indexing-stats-row font-mono text-secondary" id="indexing-stats-strip">
            <div className="indexing-stat-pill">
              <span className="stat-label">Code Sections:</span>
              <span className="stat-num text-purple font-bold">{indexingStatus.total_chunks}</span>
            </div>
            <div className="indexing-stat-pill">
              <span className="stat-label">Files Analyzed:</span>
              <span className="stat-num text-cyan font-bold">{indexingStatus.indexed_files}</span>
            </div>
            {Object.keys(indexingStatus.languages || {}).length > 0 && (
              <div className="indexing-lang-pills">
                <span className="stat-label">Languages:</span>
                {Object.entries(indexingStatus.languages).map(([lang, count]) => (
                  <span key={lang} className="lang-mini-badge">
                    {lang}: <strong>{count}</strong>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* AI Code Preparation Card & Status */}
      <section className="indexing-pipeline-card glass-card animate-fade-in" id="embedding-generation-section">
        <div className="indexing-card-header">
          <div className="indexing-title-wrap">
            <div className="indexing-icon-wrap" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l-.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </div>
            <div>
              <div className="indexing-title-row">
                <h3 className="indexing-title">AI Code Preparation</h3>
                {generatingEmbeddings ? (
                  <span className="badge badge-purple animate-pulse font-mono" id="embedding-badge-progress">
                    Preparing project for AI...
                  </span>
                ) : embeddingStatus?.status === 'ready' ? (
                  <span className="badge badge-success font-mono" id="embedding-badge-completed">
                    AI Ready ({embeddingStatus.embedded_chunks} sections prepared)
                  </span>
                ) : embeddingStatus?.status === 'partial_ready' ? (
                  <span className="badge badge-warning font-mono" id="embedding-badge-partial">
                    Partially Prepared ({embeddingStatus.embedded_chunks} / {embeddingStatus.total_chunks})
                  </span>
                ) : (
                  <span className="badge badge-warning font-mono" id="embedding-badge-pending">
                    Not Prepared
                  </span>
                )}
              </div>
              <p className="indexing-desc text-secondary font-mono">
                Prepares project for natural-language code search and AI assistance
              </p>
            </div>
          </div>

          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={triggerEmbeddingGeneration}
            disabled={generatingEmbeddings || loading || indexing || indexingStatus?.status !== 'indexed' || (indexingStatus?.total_chunks || 0) === 0}
            id="trigger-embedding-btn"
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
              className={generatingEmbeddings ? 'animate-spin' : ''}
            >
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l-.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            <span>
              {generatingEmbeddings
                ? 'Preparing project for AI...'
                : embeddingStatus?.status === 'ready'
                ? 'Refresh AI Readiness'
                : 'Prepare Project for AI'}
            </span>
          </button>
        </div>

        {/* Real Loading State */}
        {generatingEmbeddings && (
          <div className="indexing-loading-banner glass-subcard animate-fade-in" id="embedding-generating-notice">
            <div className="loading-spinner-sm"></div>
            <div className="font-mono text-sm">
              <strong>Preparing your project for AI...</strong> Analyzing code semantics and preparing search capabilities.
            </div>
          </div>
        )}

        {/* Embedding Success Message */}
        {embeddingResult && (
          <div className="indexing-success-banner glass-subcard animate-fade-in" id="embedding-success-notice">
            <div className="alert-icon text-success">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </div>
            <div className="font-mono text-sm">
              <strong>Project prepared for AI:</strong> {embeddingResult.embedded_chunks} code sections ready for intelligent search.
            </div>
          </div>
        )}

        {/* Embedding Error Message */}
        {embeddingError && (
          <div className="indexing-error-banner glass-subcard animate-fade-in" id="embedding-error-notice">
            <div className="alert-icon text-error">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </div>
            <div className="font-mono text-sm text-error">
              <strong>Preparation Notice:</strong> {embeddingError}
            </div>
          </div>
        )}

        {/* Not Indexed Warning */}
        {indexingStatus?.status !== 'indexed' && (
          <div className="indexing-empty-banner font-mono text-secondary text-sm">
            Please analyze the project code before preparing for AI.
          </div>
        )}

        {/* Embedding Details Strip */}
        {embeddingStatus?.status === 'ready' && (
          <div className="indexing-stats-row font-mono text-secondary" id="embedding-stats-strip">
            <div className="indexing-stat-pill">
              <span className="stat-label">Prepared Sections:</span>
              <span className="stat-num text-cyan font-bold">{embeddingStatus.embedded_chunks}</span>
            </div>
            <div className="indexing-stat-pill">
              <span className="stat-label">AI Readiness:</span>
              <span className="stat-num text-emerald font-bold">Ready</span>
            </div>
          </div>
        )}
      </section>

      {/* Code Search Index Card & Status */}
      <section className="indexing-pipeline-card glass-card animate-fade-in" id="vector-index-section">
        <div className="indexing-card-header">
          <div className="indexing-title-wrap">
            <div className="indexing-icon-wrap" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </div>
            <div>
              <div className="indexing-title-row">
                <h3 className="indexing-title">Code Search Index</h3>
                {buildingVectorIndex ? (
                  <span className="badge badge-purple animate-pulse font-mono" id="vector-badge-progress">
                    Preparing code search...
                  </span>
                ) : vectorIndexStatus?.status === 'ready' ? (
                  <span className="badge badge-success font-mono" id="vector-badge-ready">
                    Search Ready ({vectorIndexStatus.indexed_vectors} sections indexed)
                  </span>
                ) : vectorIndexStatus?.status === 'stale' ? (
                  <span className="badge badge-warning font-mono" id="vector-badge-stale">
                    Index Update Recommended
                  </span>
                ) : (
                  <span className="badge badge-warning font-mono" id="vector-badge-pending">
                    Not Built
                  </span>
                )}
              </div>
              <p className="indexing-desc text-secondary font-mono">
                Enables fast, intelligent code search across all files in your project
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {vectorIndexStatus?.status === 'ready' && (
              <Link
                to={`/dashboard/projects/${projectId}/search`}
                className="btn btn-secondary btn-sm"
                id="open-semantic-search-btn"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <span>Search Code</span>
              </Link>
            )}

            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={triggerVectorIndexBuild}
              disabled={
                buildingVectorIndex ||
                loading ||
                indexing ||
                generatingEmbeddings ||
                (embeddingStatus?.status !== 'ready' && (embeddingStatus?.embedded_chunks || 0) === 0)
              }
              id="trigger-vector-index-btn"
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
                className={buildingVectorIndex ? 'animate-spin' : ''}
              >
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
              <span>
                {buildingVectorIndex
                  ? 'Preparing code search...'
                  : vectorIndexStatus?.status === 'ready'
                  ? 'Update Search Index'
                  : 'Enable Code Search'}
              </span>
            </button>
          </div>
        </div>

        {/* Real Loading State */}
        {buildingVectorIndex && (
          <div className="indexing-loading-banner glass-subcard animate-fade-in" id="vector-building-notice">
            <div className="loading-spinner-sm"></div>
            <div className="font-mono text-sm">
              <strong>Preparing code search...</strong> Indexing code sections for natural language search.
            </div>
          </div>
        )}

        {/* Index Build Success Message */}
        {vectorIndexResult && (
          <div className="indexing-success-banner glass-subcard animate-fade-in" id="vector-success-notice">
            <div className="alert-icon text-success">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </div>
            <div className="font-mono text-sm">
              <strong>Code search ready:</strong> {vectorIndexResult.indexed_vectors} code sections indexed and searchable.
            </div>
          </div>
        )}

        {/* Index Build Error Message */}
        {vectorIndexError && (
          <div className="indexing-error-banner glass-subcard animate-fade-in" id="vector-error-notice">
            <div className="alert-icon text-error">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </div>
            <div className="font-mono text-sm text-error">
              <strong>Search Index Notice:</strong> {vectorIndexError}
            </div>
          </div>
        )}

        {/* AI Preparation Warning */}
        {embeddingStatus?.status !== 'ready' && (embeddingStatus?.embedded_chunks || 0) === 0 && (
          <div className="indexing-empty-banner font-mono text-secondary text-sm">
            Please prepare the project for AI before enabling code search.
          </div>
        )}

        {/* Code Search Index Details Strip */}
        {vectorIndexStatus?.status === 'ready' && (
          <div className="indexing-stats-row font-mono text-secondary" id="vector-stats-strip">
            <div className="indexing-stat-pill">
              <span className="stat-label">Searchable Sections:</span>
              <span className="stat-num text-purple font-bold">{vectorIndexStatus.indexed_vectors}</span>
            </div>
            <div className="indexing-stat-pill">
              <span className="stat-label">Search Engine:</span>
              <span className="stat-num text-cyan font-bold">Fast Retrieval</span>
            </div>
            <div className="indexing-stat-pill">
              <span className="stat-label">Semantic Match:</span>
              <span className="stat-num text-emerald font-bold">Ready</span>
            </div>
            <div className="indexing-stat-pill">
              <span className="stat-label">Index Status:</span>
              <span className="stat-num text-success font-bold">Active</span>
            </div>
          </div>
        )}
      </section>

      {/* Main Analysis Sections Grid */}
      <div className="analysis-details-grid">
        {/* Left Column: Languages (Phase 17) & File Extension Statistics (Phase 18) */}
        <div className="analysis-col-left">
          {/* Languages Section */}
          <section className="analysis-card glass-card" id="analysis-languages-card">
            <div className="card-section-header">
              <div className="header-title-group">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyan">
                  <polyline points="16 18 22 12 16 6"></polyline>
                  <polyline points="8 6 2 12 8 18"></polyline>
                </svg>
                <h3 className="card-title">Languages</h3>
              </div>
              <span className="badge badge-accent font-mono">{languageList.length} detected</span>
            </div>

            {languageList.length === 0 ? (
              <p className="text-secondary font-mono empty-section-text">No recognized language files detected.</p>
            ) : (
              <div className="languages-breakdown-wrap">
                {/* Visual Distribution Bar */}
                <div className="language-stacked-bar" aria-label="Language distribution bar">
                  {languageList.map(([lang, count]) => {
                    const pct = totalFiles > 0 ? ((count / totalFiles) * 100).toFixed(1) : 0;
                    return (
                      <div
                        key={lang}
                        className="lang-bar-segment"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: getLanguageColor(lang),
                        }}
                        title={`${lang}: ${count} files (${pct}%)`}
                      />
                    );
                  })}
                </div>

                {/* Language Rows List */}
                <div className="languages-list font-mono" id="languages-list">
                  {languageList.map(([lang, count]) => {
                    const pct = totalFiles > 0 ? ((count / totalFiles) * 100).toFixed(1) : 0;
                    const color = getLanguageColor(lang);
                    return (
                      <div key={lang} className="language-row">
                        <div className="lang-info">
                          <span className="lang-color-dot" style={{ backgroundColor: color }} />
                          <span className="lang-name">{lang}</span>
                        </div>
                        <div className="lang-stats">
                          <span className="lang-files-count">{count} {count === 1 ? 'file' : 'files'}</span>
                          <span className="lang-pct text-secondary">{pct}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </section>

          {/* File Statistics & Extension Breakdown (Phase 18) */}
          <section className="analysis-card glass-card" id="analysis-extensions-card">
            <div className="card-section-header">
              <div className="header-title-group">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-purple">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="3" y1="9" x2="21" y2="9"></line>
                  <line x1="9" y1="21" x2="9" y2="9"></line>
                </svg>
                <h3 className="card-title">File Statistics</h3>
              </div>
              <span className="badge badge-secondary font-mono">{extensionList.length} extensions</span>
            </div>

            {extensionList.length === 0 ? (
              <p className="text-secondary font-mono empty-section-text">No file extensions recorded.</p>
            ) : (
              <div className="extensions-table font-mono" id="extensions-list">
                <div className="extension-table-header">
                  <span>Extension</span>
                  <span>Count</span>
                  <span>Share</span>
                </div>
                {extensionList.map(([ext, count]) => {
                  const pct = totalFiles > 0 ? ((count / totalFiles) * 100).toFixed(1) : 0;
                  return (
                    <div key={ext} className="extension-row">
                      <span className="ext-badge">{ext}</span>
                      <span className="ext-count">{count}</span>
                      <span className="ext-pct text-secondary">{pct}%</span>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        {/* Right Column: Folder Hierarchy (Phase 19) */}
        <div className="analysis-col-right">
          <section className="analysis-card glass-card hierarchy-card" id="analysis-hierarchy-card">
            <div className="card-section-header">
              <div className="header-title-group">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                <h3 className="card-title">Folder Hierarchy</h3>
              </div>
              <span className="badge badge-secondary font-mono">{totalFolders} folders</span>
            </div>

            {/* Tree search filter */}
            <div className="tree-search-wrap">
              <input
                type="text"
                className="tree-search-input font-mono"
                placeholder="Filter files & folders..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                id="hierarchy-search-input"
              />
              {searchQuery && (
                <button
                  type="button"
                  className="search-clear-btn"
                  onClick={() => setSearchQuery('')}
                  title="Clear filter"
                >
                  ✕
                </button>
              )}
            </div>

            {/* Hierarchy Tree Viewport */}
            <div className="hierarchy-tree-area" id="hierarchy-tree-container">
              {!folder_hierarchy || !folder_hierarchy.children || folder_hierarchy.children.length === 0 ? (
                <div className="tree-empty">
                  <p className="text-secondary font-mono">No files or folders found.</p>
                </div>
              ) : (
                folder_hierarchy.children.map((child) => renderTreeNode(child, 0))
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

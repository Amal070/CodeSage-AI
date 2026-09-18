import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { SkeletonTree, SkeletonCode } from './common/Skeleton';
import LoadingState from './common/LoadingState';
import { useToast } from './common/Toast';

export default function ProjectExplorer() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const queryFile = searchParams.get('file');
  const { token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  // Project state
  const [project, setProject] = useState(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [projectError, setProjectError] = useState(null);

  // File tree state
  const [fileTree, setFileTree] = useState([]);
  const [loadingTree, setLoadingTree] = useState(true);
  const [treeError, setTreeError] = useState(null);
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');

  // Selected file state
  const [selectedPath, setSelectedPath] = useState(null);
  const [fileData, setFileData] = useState(null);
  const [loadingFile, setLoadingFile] = useState(false);
  const [fileError, setFileError] = useState(null);
  const [copySuccess, setCopySuccess] = useState(false);

  // View mode state (code vs structure)
  const [activeView, setActiveView] = useState('code'); // 'code' or 'structure'
  const [structureData, setStructureData] = useState(null);
  const [loadingStructure, setLoadingStructure] = useState(false);
  const [structureError, setStructureError] = useState(null);

  // Day 20: Function doc modal state
  const [docModalFn, setDocModalFn] = useState(null);
  const [docModalData, setDocModalData] = useState(null);
  const [docModalLoading, setDocModalLoading] = useState(false);
  const [docModalError, setDocModalError] = useState(null);
  const [docModalCopied, setDocModalCopied] = useState(false);

  // Mobile layout toggle (tree vs code)
  const [mobileActiveTab, setMobileActiveTab] = useState('tree'); // 'tree' or 'code'

  // Helper to format file size
  const formatSize = (bytes) => {
    if (!bytes && bytes !== 0) return '--';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // 1. Fetch project details
  const fetchProjectDetails = useCallback(async () => {
    if (!token || !projectId) return;
    setLoadingProject(true);
    setProjectError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (!res.ok) {
        throw new Error('Project not found or you do not have permission to view it.');
      }
      const data = await res.json();
      setProject(data);
    } catch (err) {
      setProjectError(err.message || 'Failed to load project.');
    } finally {
      setLoadingProject(false);
    }
  }, [BACKEND_URL, projectId, token, logout, navigate]);

  // 2. Fetch project file tree
  const fetchFileTree = useCallback(async () => {
    if (!token || !projectId) return;
    setLoadingTree(true);
    setTreeError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/files`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (!res.ok) {
        const errorBody = await res.json().catch(() => ({}));
        throw new Error(errorBody.detail || 'Failed to load project file tree.');
      }
      const data = await res.json();
      const tree = data.tree || [];
      setFileTree(tree);

      // Auto-expand folders
      const initialExpanded = new Set();
      tree.forEach((node) => {
        if (node.type === 'folder') {
          initialExpanded.add(node.path);
        }
      });

      if (queryFile) {
        const parts = queryFile.split('/');
        let current = '';
        for (let i = 0; i < parts.length - 1; i++) {
          current = current ? `${current}/${parts[i]}` : parts[i];
          initialExpanded.add(current);
        }
      }
      setExpandedFolders(initialExpanded);

      // Auto-select queryFile if present, or first readable file
      const findFirstFile = (nodes) => {
        for (const n of nodes) {
          if (n.type === 'file') return n.path;
          if (n.type === 'folder' && n.children) {
            const nested = findFirstFile(n.children);
            if (nested) return nested;
          }
        }
        return null;
      };

      if (queryFile) {
        setSelectedPath(queryFile);
      } else {
        const firstFile = findFirstFile(tree);
        if (firstFile && !selectedPath) {
          setSelectedPath(firstFile);
        }
      }
    } catch (err) {
      setTreeError(err.message || 'Failed to fetch project files.');
    } finally {
      setLoadingTree(false);
    }
  }, [BACKEND_URL, projectId, token, logout, navigate, selectedPath, queryFile]);

  // 3. Fetch file content
  const fetchFileContent = useCallback(
    async (filePath) => {
      if (!token || !projectId || !filePath) return;
      setLoadingFile(true);
      setFileError(null);
      setCopySuccess(false);

      try {
        const encodedPath = encodeURIComponent(filePath);
        const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/file?path=${encodedPath}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.status === 401) {
          logout();
          navigate('/login', { replace: true });
          return;
        }

        const data = await res.json().catch(() => ({}));

        if (res.status === 413) {
          setFileData({
            name: filePath.split('/').pop(),
            path: filePath,
            language: 'unknown',
            size: 0,
            is_binary: false,
            content: null,
            message: data.detail || 'This file is too large to preview.',
            is_too_large: true,
          });
          return;
        }

        if (!res.ok) {
          throw new Error(data.detail || 'Failed to load file content.');
        }

        setFileData(data);
      } catch (err) {
        setFileError(err.message || 'Failed to read file.');
        setFileData(null);
      } finally {
        setLoadingFile(false);
      }
    },
    [BACKEND_URL, projectId, token, logout, navigate]
  );

  // 4. Fetch code structure (Tree-sitter)
  const fetchStructure = useCallback(
    async (filePath) => {
      if (!token || !projectId || !filePath) return;
      setLoadingStructure(true);
      setStructureError(null);

      try {
        const encodedPath = encodeURIComponent(filePath);
        const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/parse?path=${encodedPath}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.status === 401) {
          logout();
          navigate('/login', { replace: true });
          return;
        }

        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
          throw new Error(data.detail || 'Failed to analyze code structure.');
        }

        setStructureData(data);
      } catch (err) {
        setStructureError(err.message || 'Failed to parse code structure.');
        setStructureData(null);
      } finally {
        setLoadingStructure(false);
      }
    },
    [BACKEND_URL, projectId, token, logout, navigate]
  );

  useEffect(() => {
    fetchProjectDetails();
    fetchFileTree();
  }, [fetchProjectDetails, fetchFileTree]);

  useEffect(() => {
    if (selectedPath) {
      fetchFileContent(selectedPath);
    }
  }, [selectedPath, fetchFileContent]);

  // Folder expand/collapse handler
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

  // Select file handler
  const handleSelectFile = (filePath) => {
    setSelectedPath(filePath);
    setMobileActiveTab('code'); // On mobile switch to code view automatically
    setStructureData(null);
    setStructureError(null);
    setActiveView('code');
  };

  // Trigger structure analysis
  const handleAnalyzeStructure = () => {
    setActiveView('structure');
    if (!structureData || structureData.file !== selectedPath) {
      fetchStructure(selectedPath);
    }
  };

  // Copy code to clipboard
  const handleCopyCode = async () => {
    if (!fileData || !fileData.content) return;
    try {
      await navigator.clipboard.writeText(fileData.content);
      setCopySuccess(true);
      toast.success('Code copied to clipboard');
      setTimeout(() => setCopySuccess(false), 2000);
    } catch {
      // Fallback
    }
  };

  // Day 20: Function Documentation Modal Handlers
  const handleOpenDocModal = async (fn) => {
    setDocModalFn(fn);
    setDocModalData(null);
    setDocModalError(null);
    setDocModalLoading(true);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/functions/document`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          file_path: selectedPath,
          function_name: fn.name,
          start_line: fn.line_start,
          end_line: fn.line_end,
          parent_class: fn.parent_class,
        }),
      });

      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate function documentation.');
      }
      setDocModalData(data);
    } catch (err) {
      setDocModalError(err.message || 'Error generating documentation.');
    } finally {
      setDocModalLoading(false);
    }
  };

  const handleCloseDocModal = () => {
    setDocModalFn(null);
    setDocModalData(null);
    setDocModalError(null);
  };

  const handleCopyModalMarkdown = () => {
    if (!docModalData?.documentation) return;
    navigator.clipboard.writeText(docModalData.documentation);
    setDocModalCopied(true);
    setTimeout(() => setDocModalCopied(false), 2000);
  };

  // Prepare line numbers and lines
  const codeLines = useMemo(() => {
    if (!fileData || !fileData.content) return [];
    return fileData.content.split('\n');
  }, [fileData]);

  // Recursive Tree Node Renderer
  const renderTreeNode = (node, depth = 0) => {
    const isFolder = node.type === 'folder';
    const isExpanded = expandedFolders.has(node.path);
    const isSelected = selectedPath === node.path;

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
        <div key={node.path} className="tree-folder-group">
          <div
            className={`tree-node folder-node ${isExpanded ? 'expanded' : ''}`}
            style={{ paddingLeft }}
            onClick={() => toggleFolder(node.path)}
            title={node.path}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && toggleFolder(node.path)}
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
              {isExpanded ? (
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              ) : (
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              )}
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
        key={node.path}
        className={`tree-node file-node ${isSelected ? 'selected' : ''}`}
        style={{ paddingLeft }}
        onClick={() => handleSelectFile(node.path)}
        title={node.path}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && handleSelectFile(node.path)}
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
        {node.size !== null && (
          <span className="node-size-pill">{formatSize(node.size)}</span>
        )}
      </div>
    );
  };

  if (loadingProject) {
    return (
      <LoadingState
        title="Loading project..."
        message="Retrieving workspace details from CodeSage AI"
        id="explorer-loading-state"
      />
    );
  }

  if (projectError) {
    return (
      <div className="explorer-error-state glass-card">
        <div className="error-icon-box">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
        <h2>Project Access Error</h2>
        <p className="error-message">{projectError}</p>
        <div className="error-actions">
          <Link to="/dashboard/projects" className="btn btn-primary">
            Return to Projects
          </Link>
          <button type="button" className="btn btn-ghost" onClick={fetchProjectDetails}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="project-explorer-container animate-fade-in">
      {/* Breadcrumbs and Project Header */}
      <header className="explorer-header-card glass-card">
        <div className="explorer-header-left">
          <nav className="explorer-breadcrumbs font-mono" aria-label="Breadcrumb">
            <Link to="/dashboard" className="crumb-link">Dashboard</Link>
            <span className="crumb-sep">/</span>
            <Link to="/dashboard/projects" className="crumb-link">Projects</Link>
            <span className="crumb-sep">/</span>
            <Link to={`/dashboard/projects/${projectId}`} className="crumb-link">{project?.name || 'Project'}</Link>
            <span className="crumb-sep">/</span>
            <span className="crumb-active">Explorer</span>
          </nav>

          <div className="project-title-row">
            <div className="project-header-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
            </div>
            <div>
              <h1 className="explorer-project-title">{project?.name}</h1>
              <div className="project-meta-strip">
                <span className="meta-pill font-mono">Archive: {project?.original_filename || '--'}</span>
                <span className="meta-pill font-mono">Files: {project?.file_count || 0}</span>
                <span className="meta-pill badge badge-success capitalize">{project?.status || 'uploaded'}</span>
                {project?.created_at && (
                  <span className="meta-pill text-secondary">
                    Uploaded: {new Date(project.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="explorer-header-right">
          <Link to={`/dashboard/projects/${projectId}`} className="btn btn-ghost btn-sm" id="project-overview-btn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
            <span>Overview</span>
          </Link>
          <Link to={`/dashboard/projects/${projectId}/dependencies`} className="btn btn-secondary btn-sm" id="project-dependencies-btn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3"></circle>
              <circle cx="6" cy="12" r="3"></circle>
              <circle cx="18" cy="19" r="3"></circle>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
            </svg>
            <span>Dependencies</span>
          </Link>
          {/* Day 12: Semantic Search Link */}
          <Link to={`/dashboard/projects/${projectId}/search`} className="btn btn-secondary btn-sm" id="project-search-btn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <span>Search Code</span>
          </Link>
          {/* Day 14: RAG Q&A Link */}
          <Link to={`/dashboard/projects/${projectId}/ask`} className="btn btn-secondary btn-sm" id="project-ask-btn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span>Ask CodeSage</span>
          </Link>
          {/* Day 15: AI Chat Link */}
          <Link
            to={`/dashboard/projects/${projectId}/chat`}
            className="btn btn-secondary btn-sm"
            id="project-chat-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>AI Chat</span>
          </Link>
          {/* Day 20: Function Docs Link */}
          <Link
            to={`/dashboard/projects/${projectId}/docs`}
            className="btn btn-primary btn-sm"
            id="project-docs-btn"
            style={{
              background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
              borderColor: '#38bdf8',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            <span>Function Docs</span>
          </Link>
          <Link to="/dashboard/projects" className="btn btn-ghost btn-sm" id="back-to-projects-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5"></path>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            <span>Back to Projects</span>
          </Link>
        </div>
      </header>

      {/* Mobile Tab Switcher */}
      <div className="mobile-view-switcher">
        <button
          type="button"
          className={`mobile-tab-btn ${mobileActiveTab === 'tree' ? 'active' : ''}`}
          onClick={() => setMobileActiveTab('tree')}
        >
          Files ({project?.file_count || 0})
        </button>
        <button
          type="button"
          className={`mobile-tab-btn ${mobileActiveTab === 'code' ? 'active' : ''}`}
          onClick={() => setMobileActiveTab('code')}
        >
          Code Viewer {selectedPath ? `(${selectedPath.split('/').pop()})` : ''}
        </button>
      </div>

      {/* Two-Pane Workspace Layout */}
      <div className="explorer-workspace-grid">
        {/* Left Pane: File Tree */}
        <aside className={`explorer-tree-pane glass-card ${mobileActiveTab === 'tree' ? 'mobile-show' : 'mobile-hide'}`}>
          <div className="tree-pane-header">
            <div className="tree-header-title-row">
              <span className="tree-title">PROJECT FILES</span>
              <span className="tree-file-count font-mono">{project?.file_count || 0}</span>
            </div>
            <div className="tree-search-wrap">
              <input
                type="text"
                className="tree-search-input"
                placeholder="Filter files..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                id="explorer-search-input"
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
          </div>

          <div className="tree-scrollable-area" id="file-tree-container">
            {loadingTree ? (
              <SkeletonTree items={8} />
            ) : treeError ? (
              <div className="tree-error">
                <span>{treeError}</span>
                <button type="button" className="btn btn-xs btn-ghost mt-2" onClick={fetchFileTree}>
                  Retry
                </button>
              </div>
            ) : fileTree.length === 0 ? (
              <div className="tree-empty">
                <p>No files found in this project archive.</p>
              </div>
            ) : (
              fileTree.map((node) => renderTreeNode(node, 0))
            )}
          </div>
        </aside>

        {/* Right Pane: Code Viewer */}
        <main className={`explorer-code-pane glass-card ${mobileActiveTab === 'code' ? 'mobile-show' : 'mobile-hide'}`}>
          {/* Top Bar for Current File */}
          <div className="code-pane-header">
            <div className="code-header-left">
              {selectedPath ? (
                <>
                  <span className="code-file-name font-mono">{selectedPath.split('/').pop()}</span>
                  <span className="code-file-path font-mono text-secondary">{selectedPath}</span>
                  {fileData?.language && (
                    <span className="badge badge-accent uppercase font-mono">{fileData.language}</span>
                  )}
                  {fileData?.size !== undefined && (
                    <span className="meta-pill font-mono">{formatSize(fileData.size)}</span>
                  )}
                  {codeLines.length > 0 && (
                    <span className="meta-pill font-mono">{codeLines.length} lines</span>
                  )}
                </>
              ) : (
                <span className="text-secondary font-mono">No file selected</span>
              )}
            </div>

            <div className="code-header-right">
              {selectedPath && (
                <div className="view-mode-toggle" id="view-mode-toggle">
                  <button
                    type="button"
                    className={`btn btn-xs view-toggle-btn ${activeView === 'code' ? 'active' : ''}`}
                    onClick={() => setActiveView('code')}
                    id="view-code-btn"
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="16 18 22 12 16 6"></polyline>
                      <polyline points="8 6 2 12 8 18"></polyline>
                    </svg>
                    <span>View Code</span>
                  </button>
                  <button
                    type="button"
                    className={`btn btn-xs view-toggle-btn ${activeView === 'structure' ? 'active' : ''}`}
                    onClick={handleAnalyzeStructure}
                    disabled={loadingStructure}
                    id="analyze-structure-btn"
                  >
                    {loadingStructure ? (
                      <>
                        <span className="loading-spinner-xs"></span>
                        <span>Analyzing...</span>
                      </>
                    ) : (
                      <>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="3" y="3" width="7" height="7"></rect>
                          <rect x="14" y="3" width="7" height="7"></rect>
                          <rect x="14" y="14" width="7" height="7"></rect>
                          <rect x="3" y="14" width="7" height="7"></rect>
                        </svg>
                        <span>Analyze Structure</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {activeView === 'code' && fileData?.content && (
                <button
                  type="button"
                  className="btn btn-ghost btn-sm copy-btn"
                  onClick={handleCopyCode}
                  id="copy-code-btn"
                  title="Copy code to clipboard"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    {copySuccess ? (
                      <polyline points="20 6 9 17 4 12"></polyline>
                    ) : (
                      <>
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                      </>
                    )}
                  </svg>
                  <span>{copySuccess ? 'Copied!' : 'Copy'}</span>
                </button>
              )}
            </div>
          </div>

          {/* Code Viewer / Structure Viewport */}
          <div className="code-viewport-area">
            {activeView === 'structure' ? (
              /* Code Structure View (Tree-sitter) */
              loadingStructure ? (
                <div className="code-state-box loading" id="structure-loading-state">
                  <div className="loading-spinner"></div>
                  <h4>Analyzing code structure...</h4>
                  <p className="text-secondary font-mono">Analyzing code structure in {selectedPath}...</p>
                </div>
              ) : structureError ? (
                <div className="code-state-box error" id="structure-error-state">
                  <div className="state-icon text-error">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <line x1="12" y1="8" x2="12" y2="12"></line>
                      <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                  </div>
                  <h4>Unable to analyze structure</h4>
                  <p className="text-secondary">{structureError}</p>
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost mt-2"
                    onClick={handleAnalyzeStructure}
                    id="retry-structure-btn"
                  >
                    Retry Analysis
                  </button>
                </div>
              ) : !structureData ? (
                <div className="code-state-box empty" id="structure-empty-state">
                  <div className="state-icon text-accent">
                    <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="7" height="7"></rect>
                      <rect x="14" y="3" width="7" height="7"></rect>
                      <rect x="14" y="14" width="7" height="7"></rect>
                      <rect x="3" y="14" width="7" height="7"></rect>
                    </svg>
                  </div>
                  <h3>Code Structure</h3>
                  <p className="text-secondary">Click "Analyze Structure" above to view functions, classes, and imports.</p>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm mt-2"
                    onClick={handleAnalyzeStructure}
                    disabled={loadingStructure}
                  >
                    Analyze Structure
                  </button>
                </div>
              ) : (
                <div className="code-structure-layout" id="code-structure-panel">
                  {/* Structure Header Summary */}
                  <div className="structure-summary-strip">
                    <div className="structure-summary-title">
                      <span className="structure-main-heading">Code Structure</span>
                      <span className="badge badge-accent uppercase font-mono">{structureData.language}</span>
                    </div>
                    <div className="structure-stat-pills font-mono">
                      <span className="stat-pill">
                        <span className="stat-count text-cyan">{structureData.functions?.length || 0}</span> Functions
                      </span>
                      <span className="stat-pill">
                        <span className="stat-count text-purple">{structureData.classes?.length || 0}</span> Classes
                      </span>
                      <span className="stat-pill">
                        <span className="stat-count text-emerald">{structureData.imports?.length || 0}</span> Imports
                      </span>
                    </div>
                  </div>

                  <div className="structure-grid">
                    {/* Functions Section */}
                    <section className="structure-section" id="structure-functions-section">
                      <div className="structure-section-header">
                        <div className="section-title-wrap">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                            <polyline points="2 17 12 22 22 17"></polyline>
                            <polyline points="2 12 12 17 22 12"></polyline>
                          </svg>
                          <h4 className="section-title">Functions</h4>
                        </div>
                        <span className="section-count font-mono">{structureData.functions?.length || 0}</span>
                      </div>
                      <div className="structure-items-list">
                        {(!structureData.functions || structureData.functions.length === 0) ? (
                          <div className="structure-empty-hint font-mono">No functions or methods detected.</div>
                        ) : (
                          structureData.functions.map((fn, idx) => (
                            <div key={idx} className="structure-item font-mono">
                              <div className="item-info">
                                <span className="item-name function-name">{fn.name}</span>
                                {fn.parent_class && (
                                  <span className="item-parent-badge font-mono">
                                    Class: {fn.parent_class}
                                  </span>
                                )}
                                {fn.type && (
                                  <span className={`item-type-badge ${fn.type}`}>
                                    {fn.type}
                                  </span>
                                )}
                              </div>
                              <div className="item-line-actions">
                                <span className="item-line font-mono">
                                  {fn.line_start === fn.line_end ? `line ${fn.line_start}` : `line ${fn.line_start}–${fn.line_end}`}
                                </span>
                                <button
                                  type="button"
                                  className="btn btn-xs btn-outline doc-action-btn"
                                  onClick={() => handleOpenDocModal(fn)}
                                  title={`Generate AI Documentation for ${fn.name}`}
                                >
                                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                    <polyline points="14 2 14 8 20 8"></polyline>
                                  </svg>
                                  <span>Document</span>
                                </button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </section>

                    {/* Classes Section */}
                    <section className="structure-section" id="structure-classes-section">
                      <div className="structure-section-header">
                        <div className="section-title-wrap">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="3" width="7" height="7"></rect>
                            <rect x="14" y="3" width="7" height="7"></rect>
                            <rect x="14" y="14" width="7" height="7"></rect>
                            <rect x="3" y="14" width="7" height="7"></rect>
                          </svg>
                          <h4 className="section-title">Classes</h4>
                        </div>
                        <span className="section-count font-mono">{structureData.classes?.length || 0}</span>
                      </div>
                      <div className="structure-items-list">
                        {(!structureData.classes || structureData.classes.length === 0) ? (
                          <div className="structure-empty-hint font-mono">No classes detected.</div>
                        ) : (
                          structureData.classes.map((cls, idx) => (
                            <div key={idx} className="structure-item font-mono">
                              <div className="item-info">
                                <span className="item-name class-name">{cls.name}</span>
                                <span className="item-type-badge class">class</span>
                              </div>
                              <div className="item-line font-mono">
                                {cls.line_start === cls.line_end ? `line ${cls.line_start}` : `line ${cls.line_start}–${cls.line_end}`}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </section>

                    {/* Imports Section */}
                    <section className="structure-section" id="structure-imports-section">
                      <div className="structure-section-header">
                        <div className="section-title-wrap">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="12" y1="5" x2="12" y2="19"></line>
                            <polyline points="19 12 12 19 5 12"></polyline>
                          </svg>
                          <h4 className="section-title">Imports</h4>
                        </div>
                        <span className="section-count font-mono">{structureData.imports?.length || 0}</span>
                      </div>
                      <div className="structure-items-list">
                        {(!structureData.imports || structureData.imports.length === 0) ? (
                          <div className="structure-empty-hint font-mono">No imports detected.</div>
                        ) : (
                          structureData.imports.map((imp, idx) => (
                            <div key={idx} className="structure-item font-mono">
                              <div className="item-info">
                                <span className="item-name import-name">{imp.name}</span>
                              </div>
                              <div className="item-line font-mono">
                                line {imp.line}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </section>
                  </div>
                </div>
              )
            ) : loadingFile ? (
              <div style={{ padding: '16px' }}>
                <SkeletonCode lines={16} />
              </div>
            ) : fileError ? (
              <div className="code-state-box error">
                <div className="state-icon text-error">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                </div>
                <h4>Unable to display file</h4>
                <p className="text-secondary">{fileError}</p>
                <button
                  type="button"
                  className="btn btn-sm btn-ghost mt-2"
                  onClick={() => fetchFileContent(selectedPath)}
                >
                  Retry Loading
                </button>
              </div>
            ) : !selectedPath ? (
              <div className="code-state-box empty">
                <div className="state-icon text-muted">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                </div>
                <h3>No file selected</h3>
                <p className="text-secondary">Select a file from the project explorer on the left to view its source code.</p>
              </div>
            ) : fileData?.is_binary ? (
              <div className="code-state-box binary">
                <div className="state-icon text-warning">
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                  </svg>
                </div>
                <h3>Binary File</h3>
                <p className="binary-msg">{fileData.message || 'Binary files cannot be displayed.'}</p>
                <div className="binary-meta font-mono text-secondary">
                  <span>Name: {fileData.name}</span>
                  <span>Size: {formatSize(fileData.size)}</span>
                </div>
              </div>
            ) : fileData?.is_too_large ? (
              <div className="code-state-box large-file">
                <div className="state-icon text-warning">
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                </div>
                <h3>File Too Large</h3>
                <p className="large-file-msg">{fileData.message || 'This file is too large to preview.'}</p>
              </div>
            ) : (
              /* Read-only Code Viewer with Line Numbers */
              <div className="code-editor-layout">
                {/* Gutter with Line Numbers */}
                <div className="code-gutter font-mono" aria-hidden="true">
                  {codeLines.map((_, idx) => (
                    <div key={idx} className="line-num">
                      {idx + 1}
                    </div>
                  ))}
                </div>

                {/* Code Content */}
                <pre className="code-content font-mono">
                  <code>{fileData?.content || ''}</code>
                </pre>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Day 20: Function Documentation Drawer/Modal */}
      {docModalFn && (
        <div className="doc-modal-backdrop animate-fade-in" onClick={handleCloseDocModal}>
          <div className="doc-modal-dialog glass-card" onClick={(e) => e.stopPropagation()}>
            <div className="doc-modal-header">
              <div className="doc-modal-title-group">
                <span className="badge badge-accent uppercase font-mono text-xs">AI Documentation</span>
                <h3 className="doc-modal-fn-name font-mono">{docModalFn.name}()</h3>
                <span className="text-secondary font-mono text-xs">
                  {selectedPath} &bull; Lines {docModalFn.line_start}–{docModalFn.line_end}
                </span>
              </div>

              <div className="doc-modal-actions">
                {docModalData?.documentation && (
                  <button
                    type="button"
                    className="btn btn-sm btn-primary copy-btn"
                    onClick={handleCopyModalMarkdown}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      {docModalCopied ? (
                        <polyline points="20 6 9 17 4 12"></polyline>
                      ) : (
                        <>
                          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </>
                      )}
                    </svg>
                    <span>{docModalCopied ? 'Copied!' : 'Copy Markdown'}</span>
                  </button>
                )}
                <Link
                  to={`/dashboard/projects/${projectId}/docs?fn=${encodeURIComponent(docModalFn.name)}&file=${encodeURIComponent(selectedPath || '')}`}
                  className="btn btn-sm btn-ghost"
                  title="Open in dedicated Function Docs workspace"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                  </svg>
                  <span>Full View</span>
                </Link>
                <button
                  type="button"
                  className="btn btn-sm btn-ghost close-btn"
                  onClick={handleCloseDocModal}
                >
                  &times;
                </button>
              </div>
            </div>

            <div className="doc-modal-body">
              {docModalLoading ? (
                <div className="modal-generating-state">
                  <div className="loading-spinner"></div>
                  <h4>Generating documentation with AI...</h4>
                  <p className="text-secondary font-mono text-xs">
                    Analyzing code structure &bull; Extracting context &bull; Synthesizing documentation
                  </p>
                </div>
              ) : docModalError ? (
                <div className="modal-error-state text-error">
                  <h4>Failed to generate documentation</h4>
                  <p>{docModalError}</p>
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost mt-2"
                    onClick={() => handleOpenDocModal(docModalFn)}
                  >
                    Retry
                  </button>
                </div>
              ) : docModalData ? (
                <div className="modal-doc-scroll">
                  <pre className="markdown-pre">{docModalData.documentation}</pre>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from './common/Toast';

export default function ProjectFunctionDoc() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const queryFn = searchParams.get('fn');
  const queryFile = searchParams.get('file');
  const { token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  // Project state
  const [project, setProject] = useState(null);

  // Functions state
  const [functions, setFunctions] = useState([]);
  const [loadingFunctions, setLoadingFunctions] = useState(true);
  const [functionError, setFunctionError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('all');

  // Selected function state
  const [selectedFunction, setSelectedFunction] = useState(null);
  const [docData, setDocData] = useState(null);
  const [generatingDoc, setGeneratingDoc] = useState(false);
  const [docError, setDocError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('doc'); // 'doc' | 'structured' | 'source'

  // Day 22 Export States
  const [exportingMd, setExportingMd] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportNotification, setExportNotification] = useState(null);
  const [exportError, setExportError] = useState(null);

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
        setProject(data);
        localStorage.setItem('codesage_active_project', String(projectId));
        if (data.name) {
          localStorage.setItem('codesage_active_project_name', data.name);
        }
      }
    } catch {
      // ignore
    }
  }, [BACKEND_URL, projectId, token, logout, navigate]);

  // 2. Fetch Project Functions
  const fetchFunctions = useCallback(async () => {
    if (!token || !projectId) return;
    setLoadingFunctions(true);
    setFunctionError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/functions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || 'Failed to load project functions.');
      }
      const data = await res.json();
      const fnList = data.functions || [];
      setFunctions(fnList);

      // Auto-select if query params match, or select first function
      if (queryFn) {
        const match = fnList.find(
          (f) => f.function_name === queryFn && (!queryFile || f.file_path === queryFile)
        );
        if (match) {
          setSelectedFunction(match);
          return;
        }
      }
      if (fnList.length > 0 && !selectedFunction) {
        setSelectedFunction(fnList[0]);
      }
    } catch (err) {
      setFunctionError(err.message || 'Error discovering functions.');
    } finally {
      setLoadingFunctions(false);
    }
  }, [BACKEND_URL, projectId, token, logout, navigate, queryFn, queryFile, selectedFunction]);

  useEffect(() => {
    fetchProject();
    fetchFunctions();
  }, [fetchProject, fetchFunctions]);

  // 3. Generate Documentation for Selected Function
  const handleGenerateDoc = async (fnToDoc = selectedFunction) => {
    if (!token || !projectId || !fnToDoc || generatingDoc) return;
    setGeneratingDoc(true);
    setDocError(null);
    setDocData(null);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/functions/document`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          file_path: fnToDoc.file_path,
          function_name: fnToDoc.function_name,
          start_line: fnToDoc.start_line,
          end_line: fnToDoc.end_line,
          parent_class: fnToDoc.parent_class,
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

      setDocData(data);
    } catch (err) {
      setDocError(err.message || 'Failed to generate documentation.');
    } finally {
      setGeneratingDoc(false);
    }
  };

  // Trigger doc generation on function change if not yet generated
  useEffect(() => {
    if (selectedFunction) {
      setDocData(null);
      setDocError(null);
      handleGenerateDoc(selectedFunction);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFunction?.function_name, selectedFunction?.file_path, selectedFunction?.start_line]);

  // Copy Markdown
  const handleCopyMarkdown = () => {
    if (!docData?.documentation) return;
    navigator.clipboard.writeText(docData.documentation);
    setCopied(true);
    toast.success('Function documentation copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
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

  // Day 22: Export Function Documentation as Markdown
  const handleExportFunctionMarkdown = async () => {
    if (!token || !projectId || !selectedFunction || exportingMd) return;
    setExportingMd(true);
    setExportError(null);
    try {
      const payload = {
        function_name: selectedFunction.function_name,
        file_path: selectedFunction.file_path,
        start_line: selectedFunction.start_line,
        end_line: selectedFunction.end_line,
        language: selectedFunction.language,
        parent_class: selectedFunction.parent_class,
      };
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/functions/export/markdown`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to export function documentation as Markdown.');
      }
      const cd = res.headers.get('Content-Disposition');
      let filename = `${selectedFunction.function_name}_doc.md`;
      if (cd) {
        const match = cd.match(/filename="?([^";]+)"?/);
        if (match && match[1]) filename = match[1];
      }
      const blob = await res.blob();
      downloadBlob(blob, filename);
      setExportNotification(`Downloaded ${filename}`);
      toast.success(`Exported ${filename}`);
      setTimeout(() => setExportNotification(null), 3000);
    } catch (err) {
      setExportError(err.message || 'Error exporting Markdown');
    } finally {
      setExportingMd(false);
    }
  };

  // Day 22: Export Function Documentation as PDF
  const handleExportFunctionPdf = async () => {
    if (!token || !projectId || !selectedFunction || exportingPdf) return;
    setExportingPdf(true);
    setExportError(null);
    try {
      const payload = {
        function_name: selectedFunction.function_name,
        file_path: selectedFunction.file_path,
        start_line: selectedFunction.start_line,
        end_line: selectedFunction.end_line,
        language: selectedFunction.language,
        parent_class: selectedFunction.parent_class,
      };
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/functions/export/pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to export function documentation as PDF.');
      }
      const cd = res.headers.get('Content-Disposition');
      let filename = `${selectedFunction.function_name}_doc.pdf`;
      if (cd) {
        const match = cd.match(/filename="?([^";]+)"?/);
        if (match && match[1]) filename = match[1];
      }
      const blob = await res.blob();
      downloadBlob(blob, filename);
      setExportNotification(`Downloaded ${filename}`);
      setTimeout(() => setExportNotification(null), 3000);
    } catch (err) {
      setExportError(err.message || 'Error exporting PDF');
    } finally {
      setExportingPdf(false);
    }
  };

  // Filtered functions
  const filteredFunctions = useMemo(() => {
    return functions.filter((fn) => {
      const matchSearch =
        fn.function_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        fn.file_path.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (fn.parent_class && fn.parent_class.toLowerCase().includes(searchTerm.toLowerCase()));
      const matchLang =
        selectedLanguage === 'all' || fn.language?.toLowerCase() === selectedLanguage.toLowerCase();
      return matchSearch && matchLang;
    });
  }, [functions, searchTerm, selectedLanguage]);

  // Languages present
  const availableLanguages = useMemo(() => {
    const set = new Set(functions.map((f) => f.language).filter(Boolean));
    return ['all', ...Array.from(set)];
  }, [functions]);

  return (
    <div className="function-doc-container animate-fade-in">
      {/* Top Header Navigation Strip */}
      <header className="explorer-header glass-card">
        <div className="explorer-header-left">
          <div className="project-title-group">
            <div className="project-icon-badge">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
            </div>
            <div>
              <h1 className="explorer-project-title">
                {project?.name || `Project #${projectId}`}
                <span className="badge badge-accent ml-2 uppercase font-mono text-xs">Function Docs</span>
              </h1>
              <div className="project-meta-strip">
                <span className="meta-pill font-mono">Total Functions: {functions.length}</span>
                <span className="meta-pill font-mono">AI Powered</span>
              </div>
            </div>
          </div>
        </div>

        <div className="explorer-header-right">
          <Link to={`/dashboard/projects/${projectId}`} className="btn btn-ghost btn-sm" id="fn-doc-overview-btn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
            <span>Overview</span>
          </Link>
          <Link to={`/dashboard/projects/${projectId}/explorer`} className="btn btn-secondary btn-sm" id="fn-doc-explorer-btn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"></polyline>
              <polyline points="8 6 2 12 8 18"></polyline>
            </svg>
            <span>Code Explorer</span>
          </Link>
          <Link to={`/dashboard/projects/${projectId}/search`} className="btn btn-secondary btn-sm" id="fn-doc-search-btn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <span>Search Code</span>
          </Link>
          <Link
            to={`/dashboard/projects/${projectId}/chat`}
            className="btn btn-secondary btn-sm"
            id="fn-doc-chat-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>AI Chat</span>
          </Link>
          <Link to="/dashboard/projects" className="btn btn-ghost btn-sm">
            <span>Back</span>
          </Link>
        </div>
      </header>

      {/* Main Dual-Pane Workspace */}
      <div className="function-doc-layout">
        {/* Left Sidebar: Function Directory */}
        <aside className="function-list-pane glass-card">
          <div className="pane-header">
            <div className="search-input-wrap">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
              <input
                type="text"
                placeholder="Search functions, classes, files..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input input-sm search-field"
                id="function-search-input"
              />
              {searchTerm && (
                <button
                  type="button"
                  className="clear-search-btn"
                  onClick={() => setSearchTerm('')}
                >
                  &times;
                </button>
              )}
            </div>

            {/* Language filter pills */}
            {availableLanguages.length > 2 && (
              <div className="lang-filter-pills">
                {availableLanguages.map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    className={`lang-pill ${selectedLanguage === lang ? 'active' : ''}`}
                    onClick={() => setSelectedLanguage(lang)}
                  >
                    {lang}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="function-items-scroll">
            {loadingFunctions ? (
              <div className="loading-state-pills">
                <div className="loading-spinner-sm"></div>
                <span>Scanning project functions...</span>
              </div>
            ) : functionError ? (
              <div className="error-hint text-error">{functionError}</div>
            ) : filteredFunctions.length === 0 ? (
              <div className="empty-hint">
                {functions.length === 0
                  ? 'No functions or methods found in this project.'
                  : 'No functions match your filter.'}
              </div>
            ) : (
              filteredFunctions.map((fn, idx) => {
                const isSelected =
                  selectedFunction?.function_name === fn.function_name &&
                  selectedFunction?.file_path === fn.file_path &&
                  selectedFunction?.start_line === fn.start_line;

                return (
                  <div
                    key={`${fn.file_path}-${fn.function_name}-${idx}`}
                    className={`function-card-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedFunction(fn)}
                  >
                    <div className="fn-card-top">
                      <span className="fn-name font-mono">{fn.function_name}</span>
                      <span className={`fn-type-badge ${fn.type}`}>{fn.type}</span>
                    </div>

                    {fn.parent_class && (
                      <div className="fn-class-badge font-mono">
                        Class: <span>{fn.parent_class}</span>
                      </div>
                    )}

                    <div className="fn-card-bottom font-mono text-secondary">
                      <span className="fn-path" title={fn.file_path}>
                        {fn.file_path.split('/').pop()}
                      </span>
                      <span className="fn-lines">
                        L{fn.start_line}–{fn.end_line}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Right Pane: AI Documentation & Code Viewer */}
        <main className="function-doc-main glass-card">
          {selectedFunction ? (
            <>
              {/* Function Banner Header */}
              <div className="doc-main-header">
                <div className="doc-header-info">
                  <div className="doc-fn-title-row">
                    <h2 className="doc-fn-name font-mono">{selectedFunction.function_name}()</h2>
                    <span className={`badge ${selectedFunction.type === 'method' ? 'badge-purple' : 'badge-cyan'}`}>
                      {selectedFunction.type}
                    </span>
                    {selectedFunction.parent_class && (
                      <span className="badge badge-accent">
                        Class: {selectedFunction.parent_class}
                      </span>
                    )}
                    <span className="badge badge-neutral uppercase font-mono">
                      {selectedFunction.language}
                    </span>
                  </div>
                  <div className="doc-fn-meta-row font-mono text-secondary">
                    <span className="meta-item">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                        <polyline points="13 2 13 9 20 9"></polyline>
                      </svg>
                      {selectedFunction.file_path}
                    </span>
                    <span className="meta-item">
                      Lines {selectedFunction.start_line}–{selectedFunction.end_line}
                    </span>
                  </div>
                </div>

                <div className="doc-header-actions">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleGenerateDoc(selectedFunction)}
                    disabled={generatingDoc}
                    id="regenerate-doc-btn"
                  >
                    {generatingDoc ? (
                      <>
                        <span className="loading-spinner-xs"></span>
                        <span>Analyzing...</span>
                      </>
                    ) : (
                      <>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="23 4 23 10 17 10"></polyline>
                          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                        </svg>
                        <span>Regenerate</span>
                      </>
                    )}
                  </button>

                  {docData?.documentation && (
                    <>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm copy-btn"
                        onClick={handleCopyMarkdown}
                        id="copy-doc-markdown-btn"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          {copied ? (
                            <polyline points="20 6 9 17 4 12"></polyline>
                          ) : (
                            <>
                              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </>
                          )}
                        </svg>
                        <span>{copied ? 'Copied Markdown!' : 'Copy Markdown'}</span>
                      </button>

                      {/* Day 22 Export Function Markdown */}
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={handleExportFunctionMarkdown}
                        disabled={exportingMd}
                        id="export-fn-md-btn"
                        title="Download function documentation as Markdown (.md)"
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
                          className={exportingMd ? 'animate-spin' : ''}
                        >
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                          <polyline points="7 10 12 15 17 10"></polyline>
                          <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <span>{exportingMd ? 'Exporting...' : 'Export MD'}</span>
                      </button>

                      {/* Day 22 Export Function PDF */}
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={handleExportFunctionPdf}
                        disabled={exportingPdf}
                        id="export-fn-pdf-btn"
                        title="Download function documentation as styled PDF (.pdf)"
                        style={{
                          background: 'linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)',
                          border: 'none',
                          color: '#030712',
                          fontWeight: 600,
                        }}
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
                          className={exportingPdf ? 'animate-spin' : ''}
                        >
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                          <line x1="12" y1="18" x2="12" y2="12"></line>
                          <line x1="9" y1="15" x2="15" y2="15"></line>
                        </svg>
                        <span>{exportingPdf ? 'Generating...' : 'Export PDF'}</span>
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Day 22 Export Alert Feedback */}
              {exportNotification && (
                <div className="glass-card" style={{ padding: '0.6rem 1rem', margin: '0.75rem 0', borderLeft: '3px solid #10b981', display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(16, 185, 129, 0.08)', fontSize: '0.85rem' }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                  </svg>
                  <span style={{ color: '#ecfdf5' }}>{exportNotification}</span>
                </div>
              )}
              {exportError && (
                <div className="glass-card" style={{ padding: '0.6rem 1rem', margin: '0.75rem 0', borderLeft: '3px solid #ef4444', display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(239, 68, 68, 0.08)', fontSize: '0.85rem' }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                  <span style={{ color: '#fee2e2' }}>{exportError}</span>
                </div>
              )}

              {/* View Switcher Tabs */}
              <div className="doc-view-tabs">
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'doc' ? 'active' : ''}`}
                  onClick={() => setActiveTab('doc')}
                >
                  AI Documentation
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'structured' ? 'active' : ''}`}
                  onClick={() => setActiveTab('structured')}
                >
                  Structured Breakdown
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'source' ? 'active' : ''}`}
                  onClick={() => setActiveTab('source')}
                >
                  Function Source Code
                </button>
              </div>

              {/* View Content Area */}
              <div className="doc-viewport-content">
                {generatingDoc ? (
                  <div className="generating-ai-state" id="generating-doc-state">
                    <div className="ai-pulse-orb"></div>
                    <h3>Generating Function Documentation...</h3>
                    <p className="text-secondary font-mono">
                      Analyzing function code &bull; Extracting parameters &bull; Generating documentation
                    </p>
                    <div className="ai-steps-checklist">
                      <div className="ai-step done">&bull; Code Structure Analyzed</div>
                      <div className="ai-step done">&bull; Parameters &amp; Scope Extracted</div>
                      <div className="ai-step active">&bull; Synthesizing Function Documentation</div>
                    </div>
                  </div>
                ) : docError ? (
                  <div className="doc-error-state">
                    <div className="state-icon text-error">
                      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                      </svg>
                    </div>
                    <h4>Failed to generate documentation</h4>
                    <p className="text-secondary">{docError}</p>
                    <button
                      type="button"
                      className="btn btn-sm btn-ghost mt-3"
                      onClick={() => handleGenerateDoc(selectedFunction)}
                    >
                      Retry Generation
                    </button>
                  </div>
                ) : docData ? (
                  <>
                    {/* TAB 1: Markdown Documentation View */}
                    {activeTab === 'doc' && (
                      <div className="markdown-doc-renderer" id="markdown-doc-view">
                        <pre className="markdown-pre">{docData.documentation}</pre>
                      </div>
                    )}

                    {/* TAB 2: Structured Cards View */}
                    {activeTab === 'structured' && (
                      <div className="structured-cards-grid" id="structured-doc-view">
                        {/* Purpose */}
                        <div className="struct-card struct-card-purpose">
                          <div className="struct-card-header">
                            <span className="struct-tag">Purpose</span>
                          </div>
                          <p className="struct-purpose-text">
                            {docData.purpose || 'No purpose extracted.'}
                          </p>
                        </div>

                        {/* Parameters */}
                        <div className="struct-card">
                          <div className="struct-card-header">
                            <span className="struct-tag">Parameters</span>
                            <span className="font-mono text-secondary text-xs">
                              {docData.parameters.length} declared
                            </span>
                          </div>
                          {docData.parameters.length === 0 ? (
                            <div className="struct-empty">None (Accepts no parameters)</div>
                          ) : (
                            <div className="params-list">
                              {docData.parameters.map((p, idx) => (
                                <div key={idx} className="param-item">
                                  <div className="param-top">
                                    <span className="param-name font-mono">{p.name}</span>
                                    {p.type && (
                                      <span className="param-type font-mono">{p.type}</span>
                                    )}
                                  </div>
                                  {p.description && (
                                    <div className="param-desc text-secondary">{p.description}</div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Return Value */}
                        <div className="struct-card">
                          <div className="struct-card-header">
                            <span className="struct-tag">Return Value</span>
                          </div>
                          <p className="font-mono text-secondary">
                            {docData.returns || 'None (Does not return a value)'}
                          </p>
                        </div>

                        {/* Behavior Steps */}
                        <div className="struct-card struct-card-full">
                          <div className="struct-card-header">
                            <span className="struct-tag">Execution Behavior</span>
                          </div>
                          {docData.behavior.length === 0 ? (
                            <div className="struct-empty">No sequential steps recorded.</div>
                          ) : (
                            <ol className="behavior-step-list">
                              {docData.behavior.map((b, idx) => (
                                <li key={idx} className="behavior-step-item">
                                  <span className="step-num">{idx + 1}</span>
                                  <span className="step-text">{b}</span>
                                </li>
                              ))}
                            </ol>
                          )}
                        </div>

                        {/* Important Logic */}
                        {docData.logic && docData.logic.length > 0 && (
                          <div className="struct-card">
                            <div className="struct-card-header">
                              <span className="struct-tag">Important Logic</span>
                            </div>
                            <ul className="logic-list">
                              {docData.logic.map((l, idx) => (
                                <li key={idx}>{l}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Dependencies */}
                        <div className="struct-card">
                          <div className="struct-card-header">
                            <span className="struct-tag">Dependencies</span>
                          </div>
                          {docData.dependencies.length === 0 ? (
                            <div className="struct-empty">None identified</div>
                          ) : (
                            <div className="dep-pills">
                              {docData.dependencies.map((d, idx) => (
                                <span key={idx} className="dep-pill font-mono">
                                  {d}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Exceptions / Errors */}
                        <div className="struct-card">
                          <div className="struct-card-header">
                            <span className="struct-tag">Identifiable Exceptions</span>
                          </div>
                          {docData.exceptions.length === 0 ? (
                            <div className="struct-empty">None identifiable</div>
                          ) : (
                            <ul className="logic-list text-error">
                              {docData.exceptions.map((e, idx) => (
                                <li key={idx}>{e}</li>
                              ))}
                            </ul>
                          )}
                        </div>

                        {/* Usage Example */}
                        {docData.usage_example && (
                          <div className="struct-card struct-card-full">
                            <div className="struct-card-header">
                              <span className="struct-tag">Realistic Usage Example</span>
                            </div>
                            <pre className="code-example-block font-mono">
                              {docData.usage_example}
                            </pre>
                          </div>
                        )}

                        {/* Source Location */}
                        <div className="struct-card struct-card-full struct-source-card">
                          <div className="struct-card-header">
                            <span className="struct-tag">Source Citation</span>
                          </div>
                          <div className="font-mono text-secondary">
                            File: <strong>{docData.file_path}</strong> (Lines {docData.start_line}–{docData.end_line})
                          </div>
                        </div>
                      </div>
                    )}

                    {/* TAB 3: Raw Source Code View */}
                    {activeTab === 'source' && (
                      <div className="source-preview-area" id="function-source-view">
                        <div className="source-bar font-mono">
                          <span>{docData.file_path} (Lines {docData.start_line}–{docData.end_line})</span>
                        </div>
                        <pre className="source-code-block font-mono">
                          {docData.source_code}
                        </pre>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="doc-empty-state">
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => handleGenerateDoc(selectedFunction)}
                    >
                      Generate Documentation
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="doc-no-selection-state">
              <div className="state-icon text-accent">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                  <polyline points="2 17 12 22 22 17"></polyline>
                  <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
              </div>
              <h3>Select a function to document</h3>
              <p className="text-secondary">
                Choose any function or method from the left sidebar to generate comprehensive AI documentation.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

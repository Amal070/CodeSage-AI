import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import { useToast } from './common/Toast';

export default function ApiDocumentation() {
  const { token, BACKEND_URL } = useAuth();
  const toast = useToast();
  const [catalog, setCatalog] = useState(null);
  const [selectedEndpoint, setSelectedEndpoint] = useState(null);
  const [activeTag, setActiveTag] = useState('ALL');
  const [methodFilter, setMethodFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('reference'); // 'reference' | 'ai' | 'code'
  
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiDoc, setAiDoc] = useState('');
  const [error, setError] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [exportNotification, setExportNotification] = useState('');
  const [downloadingMd, setDownloadingMd] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const API_BASE = BACKEND_URL || 'http://localhost:8000';
  const activeToken = token || localStorage.getItem('codesage_token');

  const fetchEndpoints = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = activeToken ? { Authorization: `Bearer ${activeToken}` } : {};
      const res = await fetch(`${API_BASE}/api/docs-api/endpoints`, { headers });
      if (!res.ok) {
        throw new Error(`Failed to load endpoints: ${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      setCatalog(data);
      if (data.endpoints && data.endpoints.length > 0) {
        setSelectedEndpoint(data.endpoints[0]);
      }
    } catch (err) {
      console.error(err);
      setError(err.message || 'Error connecting to backend documentation service');
    } finally {
      setLoading(false);
    }
  }, [API_BASE, activeToken]);

  useEffect(() => {
    fetchEndpoints();
  }, [fetchEndpoints]);

  const handleSelectEndpoint = (ep) => {
    setSelectedEndpoint(ep);
    setAiDoc('');
    setActiveTab('reference');
  };

  const handleGenerateAiDoc = async () => {
    if (!selectedEndpoint) return;
    setAiLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/docs-api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(activeToken ? { Authorization: `Bearer ${activeToken}` } : {}),
        },
        body: JSON.stringify({
          path: selectedEndpoint.path,
          method: selectedEndpoint.method,
        }),
      });
      if (!res.ok) {
        throw new Error(`AI generation failed (${res.status})`);
      }
      const data = await res.json();
      setAiDoc(data.markdown);
      setActiveTab('ai');
    } catch (err) {
      console.error(err);
      alert(`AI Documentation Error: ${err.message}`);
    } finally {
      setAiLoading(false);
    }
  };

  // Helper to download blob
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

  const handleDownloadMarkdown = async () => {
    if (downloadingMd) return;
    setDownloadingMd(true);
    try {
      const res = await fetch(`${API_BASE}/api/docs-api/export/markdown`, {
        headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {},
      });
      if (!res.ok) throw new Error('Failed to download Markdown API specification.');
      const blob = await res.blob();
      downloadBlob(blob, 'CodeSage_AI_API_Reference.md');
      setExportNotification('Downloaded CodeSage_AI_API_Reference.md');
      setTimeout(() => setExportNotification(''), 4000);
    } catch (err) {
      alert(`Export error: ${err.message}`);
    } finally {
      setDownloadingMd(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      const res = await fetch(`${API_BASE}/api/docs-api/export/pdf`, {
        headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {},
      });
      if (!res.ok) throw new Error('Failed to download PDF API catalog.');
      const blob = await res.blob();
      downloadBlob(blob, 'CodeSage_AI_API_Reference.pdf');
      setExportNotification('Downloaded CodeSage_AI_API_Reference.pdf');
      setTimeout(() => setExportNotification(''), 4000);
    } catch (err) {
      alert(`Export error: ${err.message}`);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleExportMarkdown = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/docs-api/markdown`, {
        headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {},
      });
      if (!res.ok) throw new Error('Failed to export markdown');
      const data = await res.json();
      
      await navigator.clipboard.writeText(data.markdown);
      setExportNotification('Full Markdown documentation copied to clipboard!');
      toast.success('API Markdown copied to clipboard');
      setTimeout(() => setExportNotification(''), 4000);
    } catch (err) {
      toast.error(`Export error: ${err.message}`);
    }
  };

  const handleCopyText = (text, id) => {
    navigator.clipboard.writeText(typeof text === 'string' ? text : JSON.stringify(text, null, 2));
    setCopiedId(id);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Filter endpoints
  const filteredEndpoints = (catalog?.endpoints || []).filter((ep) => {
    if (activeTag !== 'ALL' && ep.tag.toLowerCase() !== activeTag.toLowerCase()) {
      return false;
    }
    if (methodFilter !== 'ALL' && ep.method !== methodFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        ep.path.toLowerCase().includes(q) ||
        ep.summary.toLowerCase().includes(q) ||
        ep.description.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getMethodBadgeClass = (m) => {
    switch (m.toUpperCase()) {
      case 'GET': return 'method-get';
      case 'POST': return 'method-post';
      case 'DELETE': return 'method-delete';
      case 'PUT': return 'method-put';
      case 'PATCH': return 'method-patch';
      default: return 'method-other';
    }
  };

  const renderCurlSnippet = (ep) => {
    let curl = `curl -X ${ep.method} "${API_BASE}${ep.path}"`;
    if (ep.auth_required) {
      curl += ` \\\n  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"`;
    }
    if (ep.request_body_type === 'application/json' && ep.example_request) {
      curl += ` \\\n  -H "Content-Type: application/json" \\\n  -d '${JSON.stringify(ep.example_request)}'`;
    } else if (ep.request_body_type === 'multipart/form-data') {
      curl += ` \\\n  -F "file=@project.zip"`;
    }
    return curl;
  };

  const renderPythonSnippet = (ep) => {
    let code = `import httpx\n\n`;
    code += `headers = {}\n`;
    if (ep.auth_required) {
      code += `headers["Authorization"] = "Bearer YOUR_ACCESS_TOKEN"\n`;
    }
    if (ep.request_body_type === 'application/json' && ep.example_request) {
      code += `payload = ${JSON.stringify(ep.example_request, null, 4)}\n\n`;
      code += `response = httpx.${ep.method.toLowerCase()}("${API_BASE}${ep.path}", json=payload, headers=headers)\n`;
    } else if (ep.request_body_type === 'multipart/form-data') {
      code += `files = {"file": open("project.zip", "rb")}\n`;
      code += `response = httpx.${ep.method.toLowerCase()}("${API_BASE}${ep.path}", files=files, headers=headers)\n`;
    } else {
      code += `response = httpx.${ep.method.toLowerCase()}("${API_BASE}${ep.path}", headers=headers)\n`;
    }
    code += `print(response.status_code, response.json())`;
    return code;
  };

  return (
    <div className="api-docs-container">
      {/* Header Banner */}
      <div className="api-docs-header glass-card">
        <div className="api-docs-title-area">
          <div className="api-docs-badge-row">
            <span className="api-badge-status">Interactive Catalog</span>
            <span className="api-badge-version">v{catalog?.version || '1.0.0'}</span>
          </div>
          <h1 className="api-docs-title">API Documentation</h1>
          <p className="api-docs-subtitle">
            Interactive endpoint reference, request and response schemas, and developer guides.
          </p>
        </div>

        <div className="api-docs-actions">
          {/* Day 22 Download Markdown File */}
          <button
            type="button"
            className="btn btn-secondary api-export-btn"
            onClick={handleDownloadMarkdown}
            disabled={downloadingMd}
            id="download-api-md-btn"
            title="Download complete API reference as Markdown (.md)"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={downloadingMd ? 'animate-spin' : ''}
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            {downloadingMd ? 'Downloading...' : 'Export Markdown'}
          </button>

          {/* Day 22 Download PDF File */}
          <button
            type="button"
            className="btn btn-primary api-export-btn"
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            id="download-api-pdf-btn"
            title="Download complete API reference catalog as PDF (.pdf)"
            style={{
              background: 'linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)',
              border: 'none',
              color: '#030712',
              fontWeight: 600,
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={downloadingPdf ? 'animate-spin' : ''}
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="12" y1="18" x2="12" y2="12"></line>
              <line x1="9" y1="15" x2="15" y2="15"></line>
            </svg>
            {downloadingPdf ? 'Generating PDF...' : 'Export PDF'}
          </button>

          <button
            type="button"
            className="btn btn-secondary api-export-btn"
            onClick={handleExportMarkdown}
            title="Copy complete reference Markdown to clipboard"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            Copy Markdown
          </button>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="btn btn-outline api-swagger-link"
            title="Open native Swagger UI in new tab"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" y1="14" x2="21" y2="3"></line>
            </svg>
            Swagger /docs
          </a>
        </div>
      </div>

      {exportNotification && (
        <div className="alert-banner alert-success glass-card">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span>{exportNotification}</span>
        </div>
      )}

      {error && (
        <div className="alert-banner alert-danger glass-card">
          <span>{error}</span>
          <button className="btn btn-sm btn-outline" onClick={fetchEndpoints}>Retry</button>
        </div>
      )}

      {/* Main Workspace */}
      <div className="api-workspace-grid">
        {/* Left Sidebar: Endpoint Browser */}
        <div className="api-sidebar-panel glass-card">
          <div className="api-filter-controls">
            {/* Search Input */}
            <div className="api-search-box">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
              <input
                type="text"
                placeholder="Filter endpoints (e.g. /chat, auth)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="api-search-input"
              />
              {searchQuery && (
                <button
                  className="search-clear-btn"
                  onClick={() => setSearchQuery('')}
                >
                  ×
                </button>
              )}
            </div>

            {/* HTTP Method Filters */}
            <div className="api-method-chips">
              {['ALL', 'GET', 'POST', 'DELETE'].map((m) => (
                <button
                  key={m}
                  className={`method-chip ${methodFilter === m ? 'active' : ''}`}
                  onClick={() => setMethodFilter(m)}
                >
                  {m}
                </button>
              ))}
            </div>

            {/* Tag Pills */}
            <div className="api-tag-pills">
              <button
                className={`tag-pill ${activeTag === 'ALL' ? 'active' : ''}`}
                onClick={() => setActiveTag('ALL')}
              >
                All ({catalog?.total_endpoints || 0})
              </button>
              {(catalog?.tags || []).map((t) => (
                <button
                  key={t}
                  className={`tag-pill ${activeTag.toLowerCase() === t.toLowerCase() ? 'active' : ''}`}
                  onClick={() => setActiveTag(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Endpoint List */}
          <div className="api-endpoint-list">
            {loading ? (
              <div className="api-loading-state">
                <div className="spinner"></div>
                <span>Discovering endpoints...</span>
              </div>
            ) : filteredEndpoints.length === 0 ? (
              <div className="api-empty-state">
                <p>No endpoints match current filters.</p>
              </div>
            ) : (
              filteredEndpoints.map((ep) => {
                const isSelected = selectedEndpoint?.id === ep.id;
                return (
                  <div
                    key={ep.id}
                    className={`api-endpoint-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleSelectEndpoint(ep)}
                  >
                    <div className="ep-card-top">
                      <span className={`method-badge ${getMethodBadgeClass(ep.method)}`}>
                        {ep.method}
                      </span>
                      <span className="ep-card-path" title={ep.path}>
                        {ep.path}
                      </span>
                      {ep.auth_required ? (
                        <span className="ep-auth-badge auth-locked" title="Requires JWT Auth">
                          <Icon name="security" size={12} />
                        </span>
                      ) : (
                        <span className="ep-auth-badge auth-public" title="Public Endpoint">
                          <Icon name="monitor" size={12} />
                        </span>
                      )}
                    </div>
                    <div className="ep-card-summary">
                      {ep.summary || ep.source_function}
                    </div>
                    <div className="ep-card-meta">
                      <span className="ep-tag-label">{ep.tag}</span>
                      <span className="ep-source-hint">{ep.source_file.split('/').pop()}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Detail Pane */}
        <div className="api-detail-panel glass-card">
          {selectedEndpoint ? (
            <div className="api-detail-content">
              {/* Endpoint Banner */}
              <div className="ep-banner">
                <div className="ep-banner-main">
                  <div className="ep-method-path-group">
                    <span className={`method-badge lg ${getMethodBadgeClass(selectedEndpoint.method)}`}>
                      {selectedEndpoint.method}
                    </span>
                    <h2 className="ep-full-path">{selectedEndpoint.path}</h2>
                    <button
                      className="btn-icon copy-btn"
                      onClick={() => handleCopyText(selectedEndpoint.path, 'path')}
                      title="Copy endpoint path"
                    >
                      {copiedId === 'path' ? '✓' : '📋'}
                    </button>
                  </div>
                  <p className="ep-summary-text">{selectedEndpoint.summary}</p>
                </div>

                <div className="ep-banner-side">
                  <div className="ep-tag-box">
                    <span className="badge-label">Category:</span>
                    <span className="badge-val">{selectedEndpoint.tag}</span>
                  </div>
                  <div className={`ep-auth-box ${selectedEndpoint.auth_required ? 'locked' : 'unlocked'}`}>
                    <span className="auth-icon">{selectedEndpoint.auth_required ? '🔒' : '🌐'}</span>
                    <div className="auth-details">
                      <span className="auth-name">{selectedEndpoint.auth_type}</span>
                      <span className="auth-desc">
                        {selectedEndpoint.auth_required
                          ? 'Requires Bearer Token'
                          : 'Publicly Accessible'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Source Reference Strip */}
              <div className="ep-source-strip">
                <span className="source-label">Source Handler:</span>
                <code className="source-code-link">
                  {selectedEndpoint.source_file} : {selectedEndpoint.source_function}() ({selectedEndpoint.source_line_range})
                </code>
              </div>

              {/* Tabs */}
              <div className="ep-tabs">
                <button
                  className={`ep-tab ${activeTab === 'reference' ? 'active' : ''}`}
                  onClick={() => setActiveTab('reference')}
                >
                  Interactive Reference
                </button>
                <button
                  className={`ep-tab ${activeTab === 'ai' ? 'active' : ''}`}
                  onClick={() => setActiveTab('ai')}
                >
                  AI Developer Guide
                  {aiLoading && <span className="tab-spinner"></span>}
                </button>
                <button
                  className={`ep-tab ${activeTab === 'code' ? 'active' : ''}`}
                  onClick={() => setActiveTab('code')}
                >
                  Client Code Snippets
                </button>
              </div>

              {/* Tab 1: Interactive Reference */}
              {activeTab === 'reference' && (
                <div className="ep-tab-content">
                  {/* Description / Docstring */}
                  {selectedEndpoint.description && (
                    <div className="ep-section">
                      <h3 className="section-heading">Description & Docstring</h3>
                      <pre className="ep-docstring-box">{selectedEndpoint.description}</pre>
                    </div>
                  )}

                  {/* Path Parameters */}
                  {selectedEndpoint.path_params && selectedEndpoint.path_params.length > 0 && (
                    <div className="ep-section">
                      <h3 className="section-heading">Path Parameters</h3>
                      <table className="api-table">
                        <thead>
                          <tr>
                            <th>Parameter</th>
                            <th>Type</th>
                            <th>Required</th>
                            <th>Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedEndpoint.path_params.map((p) => (
                            <tr key={p.name}>
                              <td><code>{p.name}</code></td>
                              <td><span className="type-badge">{p.type}</span></td>
                              <td><span className="badge-required">Yes</span></td>
                              <td>{p.description || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Query Parameters */}
                  {selectedEndpoint.query_params && selectedEndpoint.query_params.length > 0 && (
                    <div className="ep-section">
                      <h3 className="section-heading">Query Parameters</h3>
                      <table className="api-table">
                        <thead>
                          <tr>
                            <th>Parameter</th>
                            <th>Type</th>
                            <th>Default</th>
                            <th>Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedEndpoint.query_params.map((q) => (
                            <tr key={q.name}>
                              <td><code>{q.name}</code></td>
                              <td><span className="type-badge">{q.type}</span></td>
                              <td><code>{q.default || 'None'}</code></td>
                              <td>{q.description || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Request Body */}
                  {selectedEndpoint.request_fields && selectedEndpoint.request_fields.length > 0 && (
                    <div className="ep-section">
                      <div className="section-header-flex">
                        <h3 className="section-heading">
                          Request Body
                          {selectedEndpoint.request_model_name && (
                            <span className="schema-model-tag">({selectedEndpoint.request_model_name})</span>
                          )}
                        </h3>
                        <span className="content-type-badge">{selectedEndpoint.request_body_type}</span>
                      </div>

                      <table className="api-table">
                        <thead>
                          <tr>
                            <th>Field</th>
                            <th>Type</th>
                            <th>Required</th>
                            <th>Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedEndpoint.request_fields.map((f) => (
                            <tr key={f.name}>
                              <td><code>{f.name}</code></td>
                              <td><span className="type-badge">{f.type}</span></td>
                              <td>
                                {f.required ? (
                                  <span className="badge-required">Required</span>
                                ) : (
                                  <span className="badge-optional">Optional</span>
                                )}
                              </td>
                              <td>{f.description || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      {selectedEndpoint.example_request && (
                        <div className="example-box">
                          <div className="example-header">
                            <span>Example Request Payload</span>
                            <button
                              className="btn-sm btn-outline copy-btn"
                              onClick={() => handleCopyText(selectedEndpoint.example_request, 'req')}
                            >
                              {copiedId === 'req' ? 'Copied!' : 'Copy JSON'}
                            </button>
                          </div>
                          <pre className="example-code">
                            {typeof selectedEndpoint.example_request === 'string'
                              ? selectedEndpoint.example_request
                              : JSON.stringify(selectedEndpoint.example_request, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Response Schema */}
                  <div className="ep-section">
                    <div className="section-header-flex">
                      <h3 className="section-heading">
                        Primary Response
                        {selectedEndpoint.response_model_name && (
                          <span className="schema-model-tag">({selectedEndpoint.response_model_name})</span>
                        )}
                      </h3>
                      <span className="status-code-badge status-200">
                        HTTP {selectedEndpoint.response_status}
                      </span>
                    </div>

                    {selectedEndpoint.response_fields && selectedEndpoint.response_fields.length > 0 && (
                      <table className="api-table">
                        <thead>
                          <tr>
                            <th>Field</th>
                            <th>Type</th>
                            <th>Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedEndpoint.response_fields.map((f) => (
                            <tr key={f.name}>
                              <td><code>{f.name}</code></td>
                              <td><span className="type-badge">{f.type}</span></td>
                              <td>{f.description || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}

                    {selectedEndpoint.example_response && (
                      <div className="example-box">
                        <div className="example-header">
                          <span>Example Response JSON</span>
                          <button
                            className="btn-sm btn-outline copy-btn"
                            onClick={() => handleCopyText(selectedEndpoint.example_response, 'res')}
                          >
                            {copiedId === 'res' ? 'Copied!' : 'Copy JSON'}
                          </button>
                        </div>
                        <pre className="example-code">
                          {typeof selectedEndpoint.example_response === 'string'
                            ? selectedEndpoint.example_response
                            : JSON.stringify(selectedEndpoint.example_response, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>

                  {/* Documented Errors */}
                  {selectedEndpoint.error_responses && selectedEndpoint.error_responses.length > 0 && (
                    <div className="ep-section">
                      <h3 className="section-heading">Error Status Codes</h3>
                      <div className="error-chips-list">
                        {selectedEndpoint.error_responses.map((err) => (
                          <div key={err.status_code} className="error-chip-item">
                            <span className="error-status-code">{err.status_code}</span>
                            <div className="error-info">
                              <span className="error-name">{err.name}</span>
                              <span className="error-desc">{err.description}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Dependencies */}
                  {selectedEndpoint.dependencies && selectedEndpoint.dependencies.length > 0 && (
                    <div className="ep-section">
                      <h3 className="section-heading">Service Dependencies</h3>
                      <div className="deps-tags">
                        {selectedEndpoint.dependencies.map((dep, idx) => (
                          <span key={idx} className="dep-tag">
                            {dep}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: AI Developer Guide */}
              {activeTab === 'ai' && (
                <div className="ep-tab-content">
                  <div className="ai-controls-bar">
                    <button
                      className="btn btn-primary generate-ai-btn"
                      onClick={handleGenerateAiDoc}
                      disabled={aiLoading}
                    >
                      {aiLoading ? (
                        <>
                          <span className="spinner-sm"></span>
                          Generating Documentation...
                        </>
                      ) : (
                        <>
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                          </svg>
                          Generate AI Documentation
                        </>
                      )}
                    </button>
                    {aiDoc && (
                      <button
                        className="btn btn-outline"
                        onClick={() => handleCopyText(aiDoc, 'aidoc')}
                      >
                        {copiedId === 'aidoc' ? 'Copied!' : 'Copy Guide Markdown'}
                      </button>
                    )}
                  </div>

                  {aiLoading ? (
                    <div className="ai-generating-placeholder">
                      <div className="spinner"></div>
                      <p>AI is analyzing endpoint schema and implementation...</p>
                    </div>
                  ) : aiDoc ? (
                    <div className="ai-markdown-viewer">
                      <pre className="markdown-pre">{aiDoc}</pre>
                    </div>
                  ) : (
                    <div className="ai-prompt-cta">
                      <h4>AI-Powered Endpoint Guide</h4>
                      <p>
                        Click "Generate AI Documentation" above to automatically generate a detailed developer guide for this endpoint.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Client Code Snippets */}
              {activeTab === 'code' && (
                <div className="ep-tab-content">
                  <div className="ep-section">
                    <div className="section-header-flex">
                      <h3 className="section-heading">cURL Command</h3>
                      <button
                        className="btn-sm btn-outline copy-btn"
                        onClick={() => handleCopyText(renderCurlSnippet(selectedEndpoint), 'curl')}
                      >
                        {copiedId === 'curl' ? 'Copied!' : 'Copy cURL'}
                      </button>
                    </div>
                    <pre className="code-block-snippet">{renderCurlSnippet(selectedEndpoint)}</pre>
                  </div>

                  <div className="ep-section">
                    <div className="section-header-flex">
                      <h3 className="section-heading">Python (HTTPX)</h3>
                      <button
                        className="btn-sm btn-outline copy-btn"
                        onClick={() => handleCopyText(renderPythonSnippet(selectedEndpoint), 'py')}
                      >
                        {copiedId === 'py' ? 'Copied!' : 'Copy Python'}
                      </button>
                    </div>
                    <pre className="code-block-snippet">{renderPythonSnippet(selectedEndpoint)}</pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="api-no-selection">
              <p>Select an endpoint from the left directory to view full documentation.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

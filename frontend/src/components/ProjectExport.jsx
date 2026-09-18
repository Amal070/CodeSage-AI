import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import { useToast } from './common/Toast';

export default function ProjectExport() {
  const { token, BACKEND_URL } = useAuth();
  const toast = useToast();

  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [downloading, setDownloading] = useState({});

  useEffect(() => {
    if (!token) return;
    fetch(`${BACKEND_URL}/api/projects`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setProjects(list);
        if (list.length > 0) {
          const savedActive = localStorage.getItem('codesage_active_project');
          const matching = list.find((p) => String(p.id) === String(savedActive));
          setSelectedProjectId(matching ? String(matching.id) : String(list[0].id));
        }
      })
      .catch(() => setProjects([]))
      .finally(() => setLoadingProjects(false));
  }, [token, BACKEND_URL]);

  const handleDownload = async (type, format, endpoint) => {
    const downloadKey = `${type}-${format}`;
    if (downloading[downloadKey]) return;

    setDownloading((prev) => ({ ...prev, [downloadKey]: true }));
    try {
      const res = await fetch(endpoint, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!res.ok) {
        throw new Error(`Failed to download ${format.toUpperCase()} export`);
      }

      const blob = await res.blob();
      const currentProject = projects.find((p) => String(p.id) === String(selectedProjectId));
      const projectName = currentProject?.name ? currentProject.name.replace(/[^a-zA-Z0-9_-]/g, '_') : 'Project';
      const filename = `${projectName}_${type}_Documentation.${format === 'markdown' ? 'md' : 'pdf'}`;

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success(`Downloaded ${filename}`);
    } catch (err) {
      toast.error(err.message || 'Export download failed. Please try again.');
    } finally {
      setDownloading((prev) => ({ ...prev, [downloadKey]: false }));
    }
  };

  const selectedProject = projects.find((p) => String(p.id) === String(selectedProjectId));

  return (
    <div className="project-analysis-container animate-fade-in" id="export-page">
      {/* Header Banner */}
      <header className="analysis-header-card glass-card">
        <div className="analysis-header-left">
          <nav className="explorer-breadcrumbs font-mono" aria-label="Breadcrumb">
            <Link to="/dashboard" className="crumb-link">Dashboard</Link>
            <span className="crumb-sep">/</span>
            <span className="crumb-active">Export</span>
          </nav>

          <div className="project-title-row">
            <div className="project-header-icon">
              <Icon name="download" size={24} />
            </div>
            <div>
              <h1 className="analysis-project-title">Export Documentation</h1>
              <p className="analysis-project-sub text-secondary font-mono">
                Download project documentation, function guides, and API specifications as Markdown or PDF
              </p>
            </div>
          </div>
        </div>

        {projects.length > 0 && (
          <div className="analysis-header-right">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <label htmlFor="export-project-select" className="text-secondary font-mono text-sm">
                Project:
              </label>
              <select
                id="export-project-select"
                value={selectedProjectId}
                onChange={(e) => {
                  setSelectedProjectId(e.target.value);
                  localStorage.setItem('codesage_active_project', e.target.value);
                }}
                className="select-input"
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  color: '#f8fafc',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  fontSize: '0.9rem',
                }}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id} style={{ background: '#0f172a', color: '#f8fafc' }}>
                    {p.name} ({p.file_count || 0} files)
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </header>

      {loadingProjects ? (
        <div className="glass-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div className="loading-spinner" style={{ margin: '0 auto 1rem' }} />
          <p className="text-secondary">Loading your projects...</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="glass-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <Icon name="folder" size={40} style={{ color: 'var(--text-secondary)' }} />
          <h3 style={{ marginTop: '1rem', color: '#f8fafc' }}>No projects available for export</h3>
          <p className="text-secondary" style={{ maxWidth: '460px', margin: '0.5rem auto 1.5rem' }}>
            Upload a project first to generate and export project documentation.
          </p>
          <Link to="/dashboard/projects" className="btn btn-primary">
            <Icon name="upload" size={16} />
            <span>Upload Project</span>
          </Link>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginTop: '1.5rem' }}>
          {/* Card 1: Project Overview Documentation */}
          <div className="card glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div className="card-header">
                <div className="card-title-group">
                  <div className="card-icon purple">
                    <Icon name="analysis" size={20} />
                  </div>
                  <div>
                    <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.1rem' }}>Project Overview</h3>
                    <p className="card-desc">Architecture summary, file statistics, and languages</p>
                  </div>
                </div>
              </div>

              <div style={{ padding: '1rem 0', color: '#cbd5e1', fontSize: '0.9rem', lineHeight: '1.6' }}>
                Includes comprehensive project metrics for <strong>{selectedProject?.name}</strong>, language breakdowns, folder structures, and overall code organization.
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '1rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() =>
                  handleDownload(
                    'Overview',
                    'markdown',
                    `${BACKEND_URL}/api/projects/${selectedProjectId}/export/markdown`
                  )
                }
                disabled={downloading['Overview-markdown']}
                id="export-overview-md-btn"
              >
                <Icon name="download" size={14} />
                <span>{downloading['Overview-markdown'] ? 'Exporting...' : 'Download Markdown'}</span>
              </button>

              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() =>
                  handleDownload(
                    'Overview',
                    'pdf',
                    `${BACKEND_URL}/api/projects/${selectedProjectId}/export/pdf`
                  )
                }
                disabled={downloading['Overview-pdf']}
                id="export-overview-pdf-btn"
              >
                <Icon name="download" size={14} />
                <span>{downloading['Overview-pdf'] ? 'Exporting...' : 'Download PDF'}</span>
              </button>
            </div>
          </div>

          {/* Card 2: Function Documentation */}
          <div className="card glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div className="card-header">
                <div className="card-title-group">
                  <div className="card-icon cyan">
                    <Icon name="code" size={20} />
                  </div>
                  <div>
                    <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.1rem' }}>Function Documentation</h3>
                    <p className="card-desc">Function signatures, parameters, and explanations</p>
                  </div>
                </div>
              </div>

              <div style={{ padding: '1rem 0', color: '#cbd5e1', fontSize: '0.9rem', lineHeight: '1.6' }}>
                Complete catalog of functions, methods, classes, and their generated documentation across the codebase.
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '1rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() =>
                  handleDownload(
                    'Functions',
                    'markdown',
                    `${BACKEND_URL}/api/projects/${selectedProjectId}/functions/export/markdown`
                  )
                }
                disabled={downloading['Functions-markdown']}
                id="export-functions-md-btn"
              >
                <Icon name="download" size={14} />
                <span>{downloading['Functions-markdown'] ? 'Exporting...' : 'Download Markdown'}</span>
              </button>

              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() =>
                  handleDownload(
                    'Functions',
                    'pdf',
                    `${BACKEND_URL}/api/projects/${selectedProjectId}/functions/export/pdf`
                  )
                }
                disabled={downloading['Functions-pdf']}
                id="export-functions-pdf-btn"
              >
                <Icon name="download" size={14} />
                <span>{downloading['Functions-pdf'] ? 'Exporting...' : 'Download PDF'}</span>
              </button>
            </div>
          </div>

          {/* Card 3: API Documentation */}
          <div className="card glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div className="card-header">
                <div className="card-title-group">
                  <div className="card-icon emerald">
                    <Icon name="api" size={20} />
                  </div>
                  <div>
                    <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.1rem' }}>API Documentation</h3>
                    <p className="card-desc">Interactive endpoint reference and schemas</p>
                  </div>
                </div>
              </div>

              <div style={{ padding: '1rem 0', color: '#cbd5e1', fontSize: '0.9rem', lineHeight: '1.6' }}>
                Full OpenAPI specification export including route endpoints, methods, parameters, request bodies, and responses.
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '1rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() =>
                  handleDownload(
                    'API',
                    'markdown',
                    `${BACKEND_URL}/api/docs-api/export/markdown`
                  )
                }
                disabled={downloading['API-markdown']}
                id="export-api-md-btn"
              >
                <Icon name="download" size={14} />
                <span>{downloading['API-markdown'] ? 'Exporting...' : 'Download Markdown'}</span>
              </button>

              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() =>
                  handleDownload(
                    'API',
                    'pdf',
                    `${BACKEND_URL}/api/docs-api/export/pdf`
                  )
                }
                disabled={downloading['API-pdf']}
                id="export-api-pdf-btn"
              >
                <Icon name="download" size={14} />
                <span>{downloading['API-pdf'] ? 'Exporting...' : 'Download PDF'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

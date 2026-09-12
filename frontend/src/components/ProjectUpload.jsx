import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProjectUpload() {
  const { token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadedProject, setUploadedProject] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);

  // Helper to format file sizes nicely (Bytes, KB, MB)
  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Fetch user's existing projects
  const fetchProjects = async () => {
    if (!token) return;
    setLoadingProjects(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch {
      // Non-blocking
    } finally {
      setLoadingProjects(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [token]);

  // Handle file selection
  const handleFileSelect = (file) => {
    setErrorMessage(null);
    setUploadSuccess(false);
    setUploadedProject(null);

    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.zip')) {
      setErrorMessage('Only ZIP archives (.zip) are allowed. Please select a valid ZIP file.');
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setErrorMessage('The selected ZIP file is empty (0 bytes).');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const onFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  // Drag and Drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const resetSelection = () => {
    setSelectedFile(null);
    setUploadProgress(0);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Real upload execution with XMLHttpRequest for true progress events
  const handleUpload = () => {
    if (!selectedFile || uploading) return;

    setUploading(true);
    setUploadProgress(0);
    setErrorMessage(null);
    setUploadSuccess(false);

    const formData = new FormData();
    formData.append('file', selectedFile);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BACKEND_URL}/api/projects/upload`);

    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    // Real upload progress tracking
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setUploadProgress(percent);
      }
    };

    xhr.onload = () => {
      if (xhr.status === 201) {
        try {
          const response = JSON.parse(xhr.responseText);
          setUploadSuccess(true);
          setUploadedProject(response.project);
          setSelectedFile(null);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
          fetchProjects();
        } catch {
          setErrorMessage('Project uploaded, but failed to parse server response.');
        }
      } else if (xhr.status === 401) {
        setErrorMessage('Your session has expired. Please log in again.');
        logout();
        navigate('/login', { replace: true });
      } else {
        let errText = 'Upload failed. Please verify your ZIP file and try again.';
        try {
          const res = JSON.parse(xhr.responseText);
          if (res.detail) {
            errText = typeof res.detail === 'string' ? res.detail : JSON.stringify(res.detail);
          }
        } catch {}
        setErrorMessage(errText);
      }
      setUploading(false);
    };

    xhr.onerror = () => {
      setErrorMessage('Network connection error occurred while uploading.');
      setUploading(false);
    };

    xhr.send(formData);
  };

  return (
    <div className="project-upload-container animate-fade-in">
      {/* Hero Header */}
      <section className="upload-hero-banner glass-card">
        <div className="upload-hero-left">
          <div className="upload-icon-badge">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
          </div>
          <div>
            <div className="upload-tag-row">
              <span className="pill-badge pill-purple">Day 5 Active</span>
              <span className="pill-badge pill-cyan">Repository Ingestion</span>
            </div>
            <h1 className="upload-page-title">Upload Your Project</h1>
            <p className="upload-page-subtitle">
              Upload your codebase archive as a ZIP file to unpack, index files, and begin working with CodeSage AI.
            </p>
          </div>
        </div>

        <div className="upload-hero-right">
          <Link to="/dashboard" className="btn btn-secondary btn-sm" id="upload-back-dashboard-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
            <span>Dashboard</span>
          </Link>
        </div>
      </section>

      {/* Main Upload Card */}
      <div className="card glass-card upload-card-main">
        {/* Error Alert */}
        {errorMessage && (
          <div className="auth-alert error animate-shake" role="alert">
            <div className="alert-icon-wrap">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </div>
            <div className="alert-text">
              <strong>Upload Error:</strong> {errorMessage}
            </div>
            <button
              type="button"
              className="alert-close-btn"
              onClick={() => setErrorMessage(null)}
              aria-label="Dismiss error"
            >
              &times;
            </button>
          </div>
        )}

        {/* Success Alert / Card */}
        {uploadSuccess && uploadedProject && (
          <div className="upload-success-banner animate-fade-in">
            <div className="success-icon-wrap">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </div>
            <div className="success-details">
              <h3>Project Uploaded Successfully!</h3>
              <p>
                <strong>{uploadedProject.name}</strong> was safely unpacked into your workspace.
              </p>
              <div className="success-meta-chips">
                <span className="success-chip">
                  <strong>Archive:</strong> {uploadedProject.original_filename}
                </span>
                <span className="success-chip">
                  <strong>Files:</strong> {uploadedProject.file_count}
                </span>
                <span className="success-chip">
                  <strong>Status:</strong> {uploadedProject.status}
                </span>
              </div>
            </div>
            <div className="success-actions">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setUploadSuccess(false)}
                id="upload-another-btn"
              >
                Upload Another
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => navigate(`/dashboard/projects/${uploadedProject.id}`)}
                id="success-open-explorer-btn"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                </svg>
                <span>Open in Explorer</span>
              </button>
            </div>
          </div>
        )}

        {/* Drag & Drop Dropzone */}
        <div
          className={`upload-dropzone ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'file-ready' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => {
            if (!uploading && !selectedFile && fileInputRef.current) {
              fileInputRef.current.click();
            }
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            className="file-input-hidden"
            onChange={onFileInputChange}
            disabled={uploading}
            id="project-zip-input"
          />

          {!selectedFile ? (
            <div className="dropzone-idle">
              <div className="dropzone-icon-circle">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
              </div>
              <h3 className="dropzone-title">Choose a ZIP project file</h3>
              <p className="dropzone-hint">
                Drag and drop your project ZIP here, or <span className="browse-text">browse files</span>
              </p>
              <div className="dropzone-requirements">
                <span className="req-pill">Format: .zip only</span>
                <span className="req-pill">Max size: 100 MB</span>
                <span className="req-pill">Path traversal safe</span>
              </div>
            </div>
          ) : (
            <div className="dropzone-selected-file animate-fade-in" onClick={(e) => e.stopPropagation()}>
              <div className="file-preview-card">
                <div className="file-preview-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                  </svg>
                </div>
                <div className="file-preview-meta">
                  <span className="file-preview-name font-mono" id="selected-file-name">
                    {selectedFile.name}
                  </span>
                  <div className="file-preview-sub">
                    <span className="file-preview-size font-mono" id="selected-file-size">
                      {formatFileSize(selectedFile.size)}
                    </span>
                    <span className="file-status-tag">Ready for Ingestion</span>
                  </div>
                </div>

                {!uploading && (
                  <button
                    type="button"
                    className="btn-remove-file"
                    onClick={resetSelection}
                    title="Remove selected file"
                    id="remove-selected-file-btn"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                )}
              </div>

              {/* Real Upload Progress Bar */}
              {uploading && (
                <div className="upload-progress-wrap animate-fade-in">
                  <div className="progress-info-row">
                    <span className="progress-label">
                      <span className="spinner"></span> Uploading project...
                    </span>
                    <span className="progress-percent font-mono" id="upload-progress-percent">
                      {uploadProgress}%
                    </span>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{ width: `${uploadProgress}%` }}
                      id="upload-progress-bar"
                    ></div>
                  </div>
                </div>
              )}

              {/* Upload Action Button */}
              {!uploading && (
                <div className="upload-actions-bar">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      if (fileInputRef.current) fileInputRef.current.click();
                    }}
                    id="change-file-btn"
                  >
                    Choose Different File
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary btn-upload-submit"
                    onClick={handleUpload}
                    id="upload-project-submit-btn"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                      <polyline points="17 8 12 3 7 8"></polyline>
                      <line x1="12" y1="3" x2="12" y2="15"></line>
                    </svg>
                    <span>Upload Project</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* User's Existing Projects Section */}
      <section className="existing-projects-section">
        <div className="section-header-row">
          <div>
            <h2 className="section-title">Your Workspaces &amp; Projects</h2>
            <p className="section-desc">Uploaded projects persisted in PostgreSQL</p>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={fetchProjects}
            disabled={loadingProjects}
            id="refresh-projects-btn"
            title="Refresh project list"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={loadingProjects ? 'animate-spin' : ''}>
              <path d="M23 4v6h-6"></path>
              <path d="M1 20v-6h6"></path>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            <span>{loadingProjects ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>

        {projects.length === 0 ? (
          <div className="card glass-card empty-projects-card">
            <div className="empty-projects-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
            </div>
            <h3>No projects uploaded yet</h3>
            <p>Upload a project ZIP file above to start analyzing code with CodeSage AI.</p>
          </div>
        ) : (
          <div className="projects-grid">
            {projects.map((proj) => (
              <div key={proj.id} className="card glass-card project-record-card" id={`project-card-${proj.id}`}>
                <div className="project-card-header">
                  <div className="project-card-title-wrap">
                    <div className="project-icon-box">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                      </svg>
                    </div>
                    <div>
                      <h3 className="project-record-name">{proj.name}</h3>
                      <span className="project-archive-tag font-mono">{proj.original_filename}</span>
                    </div>
                  </div>
                  <span className="badge badge-success capitalize">{proj.status}</span>
                </div>

                <div className="project-stats-strip">
                  <div className="p-stat">
                    <span className="p-stat-label">Files</span>
                    <span className="p-stat-val font-mono">{proj.file_count}</span>
                  </div>
                  <div className="p-stat">
                    <span className="p-stat-label">Lines</span>
                    <span className="p-stat-val font-mono">{proj.lines_of_code || '--'}</span>
                  </div>
                  <div className="p-stat">
                    <span className="p-stat-label">Uploaded</span>
                    <span className="p-stat-val">
                      {proj.created_at ? new Date(proj.created_at).toLocaleDateString() : '--'}
                    </span>
                  </div>
                </div>

                <div className="project-card-footer">
                  <Link
                    to={`/dashboard/projects/${proj.id}`}
                    className="btn btn-primary btn-sm btn-open-project"
                    id={`open-project-btn-${proj.id}`}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="7" height="7"></rect>
                      <rect x="14" y="3" width="7" height="7"></rect>
                      <rect x="14" y="14" width="7" height="7"></rect>
                      <rect x="3" y="14" width="7" height="7"></rect>
                    </svg>
                    <span>Open Project</span>
                  </Link>
                  <Link
                    to={`/dashboard/projects/${proj.id}/explorer`}
                    className="btn btn-ghost btn-sm"
                    id={`explore-code-btn-${proj.id}`}
                    title="Jump directly to File Explorer"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="16 18 22 12 16 6"></polyline>
                      <polyline points="8 6 2 12 8 18"></polyline>
                    </svg>
                    <span>Explore Code</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

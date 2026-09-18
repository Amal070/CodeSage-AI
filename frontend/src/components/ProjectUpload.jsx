import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import Button from './common/Button';
import { SkeletonCard } from './common/Skeleton';
import { useToast } from './common/Toast';

export default function ProjectUpload() {
  const { token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
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
  const fetchProjects = useCallback(async () => {
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
        setProjects(Array.isArray(data) ? data : []);
      }
    } catch {
      // Non-blocking
    } finally {
      setLoadingProjects(false);
    }
  }, [BACKEND_URL, token, logout, navigate]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Handle file selection
  const handleFileSelect = (file) => {
    setErrorMessage(null);
    setUploadSuccess(false);
    setUploadedProject(null);

    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.zip')) {
      const err = 'Only ZIP archives (.zip) are allowed. Please select a valid ZIP file.';
      setErrorMessage(err);
      toast.error(err);
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      const err = 'The selected ZIP file is empty (0 bytes).';
      setErrorMessage(err);
      toast.error(err);
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
          toast.success(`Project "${response.project.name}" uploaded and unpacked!`);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
          fetchProjects();
        } catch {
          const err = 'Project uploaded, but failed to parse server response.';
          setErrorMessage(err);
          toast.error(err);
        }
      } else if (xhr.status === 401) {
        const err = 'Your session has expired. Please log in again.';
        setErrorMessage(err);
        toast.error(err);
        logout();
        navigate('/login', { replace: true });
      } else {
        let errText = 'Upload failed. Please verify your ZIP file and try again.';
        try {
          const res = JSON.parse(xhr.responseText);
          if (res.detail) {
            errText = typeof res.detail === 'string' ? res.detail : JSON.stringify(res.detail);
          }
        } catch {
          // Ignore JSON parse error and use fallback error text
        }
        setErrorMessage(errText);
        toast.error(errText);
      }
      setUploading(false);
    };

    xhr.onerror = () => {
      const err = 'Network connection error occurred while uploading.';
      setErrorMessage(err);
      toast.error(err);
      setUploading(false);
    };

    xhr.send(formData);
  };

  // Contextual step message during upload
  const getUploadStepMessage = () => {
    if (uploadProgress < 40) return `Uploading project (${uploadProgress}%)...`;
    if (uploadProgress < 75) return 'Analyzing project...';
    if (uploadProgress < 100) return 'Preparing your project...';
    return 'Ready ✓';
  };

  return (
    <div className="project-upload-container animate-fade-in">
      {/* Hero Header */}
      <section className="upload-hero-banner glass-card">
        <div className="upload-hero-left">
          <div className="upload-icon-badge">
            <Icon name="upload" size={28} />
          </div>
          <div>
            <div className="upload-tag-row">
              <span className="pill-badge pill-purple">Project Workspace</span>
              <span className="pill-badge pill-cyan">ZIP Archive</span>
            </div>
            <h1 className="upload-page-title">Upload Your Project</h1>
            <p className="upload-page-subtitle">
              Upload your project ZIP file and let CodeSage AI analyze it.
            </p>
          </div>
        </div>

        <div className="upload-hero-right">
          <Link to="/dashboard" className="btn btn-secondary btn-sm" id="upload-back-dashboard-btn">
            <Icon name="dashboard" size={14} />
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
              <Icon name="error" size={18} />
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
              <Icon name="x" size={14} />
            </button>
          </div>
        )}

        {/* Success Alert / Card */}
        {uploadSuccess && uploadedProject && (
          <div className="upload-success-banner animate-fade-in">
            <div className="success-icon-wrap">
              <Icon name="check" size={24} />
            </div>
            <div className="success-content">
              <h3>Project Uploaded &amp; Ready!</h3>
              <p>
                Repository <strong>{uploadedProject.name}</strong> was extracted successfully ({uploadedProject.file_count} files).
              </p>
              <div className="success-actions-row">
                <Link
                  to={`/dashboard/projects/${uploadedProject.id}`}
                  className="btn btn-primary btn-sm"
                  id="view-analysis-after-upload-btn"
                >
                  <Icon name="analysis" size={14} />
                  <span>Inspect Structure &amp; Analysis</span>
                </Link>
                <Link
                  to={`/dashboard/projects/${uploadedProject.id}/explorer`}
                  className="btn btn-secondary btn-sm"
                  id="explore-code-after-upload-btn"
                >
                  <Icon name="files" size={14} />
                  <span>Browse File Explorer</span>
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Dropzone Container */}
        <div
          className={`upload-dropzone ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => {
            if (!selectedFile && !uploading && fileInputRef.current) {
              fileInputRef.current.click();
            }
          }}
          id="project-dropzone"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,application/zip,application/x-zip-compressed"
            onChange={onFileInputChange}
            className="file-input-hidden"
            id="project-file-input"
          />

          {!selectedFile ? (
            <div className="dropzone-idle-content">
              <div className="dropzone-cloud-icon">
                <Icon name="upload" size={40} />
              </div>
              <h3 className="dropzone-title">
                {dragActive ? 'Drop your ZIP archive here' : 'Drag & drop project ZIP archive here'}
              </h3>
              <p className="dropzone-sub">
                Supports complete codebases including Python, JavaScript, TypeScript, Java, and C/C++.
              </p>
              <div className="dropzone-badge-row">
                <span className="filetype-badge font-mono">.ZIP ONLY</span>
                <span className="filetype-badge font-mono">MAX 50MB</span>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm dropzone-browse-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  if (fileInputRef.current) fileInputRef.current.click();
                }}
                id="browse-files-btn"
              >
                Browse Files
              </button>
            </div>
          ) : (
            <div className="dropzone-selected-content" onClick={(e) => e.stopPropagation()}>
              <div className="file-preview-card">
                <div className="file-preview-icon">
                  <Icon name="folder" size={32} />
                </div>
                <div className="file-preview-meta">
                  <span className="file-preview-name font-mono" id="selected-file-name">
                    {selectedFile.name}
                  </span>
                  <div className="file-preview-sub">
                    <span className="file-preview-size font-mono" id="selected-file-size">
                      {formatFileSize(selectedFile.size)}
                    </span>
                    <span className="file-status-tag">Ready for Analysis</span>
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
                    <Icon name="x" size={16} />
                  </button>
                )}
              </div>

              {/* Real Upload Progress Bar */}
              {uploading && (
                <div className="upload-progress-wrap animate-fade-in">
                  <div className="progress-info-row">
                    <span className="progress-label">
                      <Icon name="spinner" size={14} className="animate-spin" /> {getUploadStepMessage()}
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

                  <Button
                    variant="primary"
                    loading={uploading}
                    loadingText="Uploading..."
                    icon="upload"
                    onClick={handleUpload}
                    id="upload-project-submit-btn"
                  >
                    Upload Project
                  </Button>
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
            <h2 className="section-title">Your Projects</h2>
            <p className="section-desc">Manage and explore your uploaded software projects</p>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={fetchProjects}
            disabled={loadingProjects}
            id="refresh-projects-btn"
            title="Refresh project list"
          >
            <Icon name="refresh" size={14} className={loadingProjects ? 'animate-spin' : ''} />
            <span>{loadingProjects ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>

        {loadingProjects ? (
          <div className="projects-grid">
            <SkeletonCard height="160px" />
            <SkeletonCard height="160px" />
          </div>
        ) : projects.length === 0 ? (
          <div className="card glass-card empty-projects-card">
            <div className="empty-projects-icon">
              <Icon name="folder" size={32} />
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
                      <Icon name="folder" size={20} />
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
                    <Icon name="analysis" size={14} />
                    <span>Analyze Project</span>
                  </Link>
                  <Link
                    to={`/dashboard/projects/${proj.id}/explorer`}
                    className="btn btn-ghost btn-sm"
                    id={`explore-code-btn-${proj.id}`}
                    title="Jump directly to File Explorer"
                  >
                    <Icon name="code" size={14} />
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

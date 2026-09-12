export default function ProjectsPlaceholder() {
  return (
    <div className="projects-placeholder-container animate-fade-in">
      {/* Header Banner */}
      <div className="placeholder-hero-card glass-card">
        <div className="placeholder-hero-left">
          <div className="placeholder-icon-wrap">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              <line x1="12" y1="11" x2="12" y2="17"></line>
              <line x1="9" y1="14" x2="15" y2="14"></line>
            </svg>
          </div>
          <div>
            <div className="placeholder-badge-row">
              <span className="pill-badge pill-purple">Scheduled for Day 5</span>
              <span className="pill-badge pill-cyan">Repository Workspace</span>
            </div>
            <h2>Project Management &amp; Codebase Ingestion</h2>
            <p className="placeholder-desc">
              Repository ZIP upload, intelligent AST code parsing, and multi-file exploration capabilities will be activated in Day 5.
            </p>
          </div>
        </div>

        <div className="placeholder-hero-right">
          <button
            type="button"
            className="btn btn-secondary btn-disabled"
            disabled
            id="upload-placeholder-btn"
            title="Upload will be enabled in Day 5"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span>Upload ZIP (Day 5)</span>
          </button>
        </div>
      </div>

      {/* Feature Preview Cards */}
      <div className="roadmap-grid">
        <div className="card glass-card roadmap-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon cyan">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                  <line x1="12" y1="22.08" x2="12" y2="12"></line>
                </svg>
              </div>
              <div>
                <h3>Day 5: Archive Ingestion</h3>
                <p className="card-desc">ZIP extraction &amp; sanitized local persistence</p>
              </div>
            </div>
            <span className="badge badge-info">Next Phase</span>
          </div>
          <p className="roadmap-text">
            Upload single ZIP files up to 50MB, automatically extract project hierarchies, analyze file extensions, and index files into PostgreSQL.
          </p>
        </div>

        <div className="card glass-card roadmap-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon purple">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="16 18 22 12 16 6"></polyline>
                  <polyline points="8 6 2 12 8 18"></polyline>
                </svg>
              </div>
              <div>
                <h3>Day 6: Tree-Sitter AST</h3>
                <p className="card-desc">Deep structural grammar parsing</p>
              </div>
            </div>
            <span className="badge badge-purple">Upcoming</span>
          </div>
          <p className="roadmap-text">
            Extract functions, classes, dependencies, and docstrings across Python, JavaScript, and TypeScript with language-aware Tree-sitter parsers.
          </p>
        </div>

        <div className="card glass-card roadmap-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon emerald">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                </svg>
              </div>
              <div>
                <h3>Day 7: Vector Embeddings &amp; RAG</h3>
                <p className="card-desc">Conversational codebase intelligence</p>
              </div>
            </div>
            <span className="badge badge-success">Upcoming</span>
          </div>
          <p className="roadmap-text">
            High-density vector embeddings persisted into FAISS vector indexes, enabling context-grounded AI conversational assistance.
          </p>
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import { SkeletonMetric } from './common/Skeleton';

export default function DashboardOverview() {
  const { user, token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();

  const [userProjects, setUserProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [openDropdownId, setOpenDropdownId] = useState(null);

  // Fetch projects to show real counts and recent project list
  const loadProjects = useCallback(async () => {
    if (!token) return;
    setLoadingProjects(true);
    setFetchError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      if (!res.ok) {
        throw new Error('Unable to load projects from server.');
      }

      const data = await res.json();
      const list = Array.isArray(data) ? data : [];
      setUserProjects(list);

      // If active project is not set, set to the first project
      if (list.length > 0 && !localStorage.getItem('codesage_active_project')) {
        localStorage.setItem('codesage_active_project', String(list[0].id));
        if (list[0].name) {
          localStorage.setItem('codesage_active_project_name', list[0].name);
        }
      }
    } catch (err) {
      setFetchError(err.message || 'Unable to load projects. Please try again.');
    } finally {
      setLoadingProjects(false);
    }
  }, [token, BACKEND_URL, logout, navigate]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Close dropdown menu when clicking outside
  useEffect(() => {
    const handleWindowClick = () => setOpenDropdownId(null);
    window.addEventListener('click', handleWindowClick);
    return () => window.removeEventListener('click', handleWindowClick);
  }, []);

  const handleSetActiveProject = (proj) => {
    if (!proj) return;
    localStorage.setItem('codesage_active_project', String(proj.id));
    if (proj.name) {
      localStorage.setItem('codesage_active_project_name', proj.name);
    }
  };

  const totalFiles = userProjects.reduce((acc, p) => acc + (p.file_count || 0), 0);

  // Real Application-level metrics
  const metrics = [
    {
      id: 'metric-projects',
      label: 'Projects',
      value: String(userProjects.length),
      description: 'Active workspaces',
      tag: 'Workspaces',
      tagColor: 'cyan',
      icon: 'projects',
    },
    {
      id: 'metric-files',
      label: 'Files Analyzed',
      value: String(totalFiles),
      description: 'Analyzed source files',
      tag: 'Source Files',
      tagColor: 'purple',
      icon: 'files',
    },
    {
      id: 'metric-docs',
      label: 'Documentation',
      value: userProjects.length > 0 ? 'Ready' : '--',
      description: 'Functions & API guides',
      tag: 'Auto-Generated',
      tagColor: 'amber',
      icon: 'docs',
    },
    {
      id: 'metric-ai-questions',
      label: 'AI Assistant',
      value: userProjects.length > 0 ? 'Ready' : 'Idle',
      description: 'Interactive code Q&A',
      tag: 'Ask AI',
      tagColor: 'emerald',
      icon: 'chat',
    },
  ];

  // Curated Quick Actions (Only supported capabilities)
  const quickActions = [
    {
      id: 'qa-upload',
      title: 'New Project',
      description: 'Upload and analyze a codebase ZIP archive.',
      icon: 'upload',
      color: 'cyan',
      to: '/dashboard/projects',
      btnText: 'Upload Project',
    },
    {
      id: 'qa-explorer',
      title: 'Explore Code',
      description: 'Browse directory trees, inspect source code, and view structure.',
      icon: 'code',
      color: 'purple',
      to: '/dashboard/explorer',
      btnText: 'Explore Code',
    },
    {
      id: 'qa-chat',
      title: 'Ask AI',
      description: 'Ask questions about your codebase and get answers with code references.',
      icon: 'chat',
      color: 'emerald',
      to: '/dashboard/chat',
      btnText: 'Ask AI',
    },
    {
      id: 'qa-analysis',
      title: 'Analyze Project',
      description: 'Understand your project’s structure, files, and technologies.',
      icon: 'analysis',
      color: 'amber',
      to: '/dashboard/analysis',
      btnText: 'Analyze Project',
    },
    {
      id: 'qa-search',
      title: 'Search Code',
      description: 'Find relevant code and symbols across your project.',
      icon: 'search',
      color: 'blue',
      to: '/dashboard/search',
      btnText: 'Search Code',
    },
    {
      id: 'qa-docs',
      title: 'Documentation',
      description: 'Generate and explore function documentation and API guides.',
      icon: 'docs',
      color: 'pink',
      to: '/dashboard/docs',
      btnText: 'View Docs',
    },
    {
      id: 'qa-export',
      title: 'Export Guides',
      description: 'Download comprehensive project documentation as Markdown or PDF.',
      icon: 'download',
      color: 'emerald',
      to: '/dashboard/export',
      btnText: 'Export Docs',
    },
  ];

  // Suggested prompt ideas for AI Assistant
  const suggestedPrompts = [
    'Explain the authentication and authorization flow.',
    'Where is the database connection configured?',
    'How does the project handle file uploads and archiving?',
    'What are the core external packages and dependencies?',
  ];

  const userName = user?.name || 'Developer';

  // Filter projects by user search
  const filteredProjects = userProjects.filter((p) => {
    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    return (
      (p.name && p.name.toLowerCase().includes(q)) ||
      (p.original_filename && p.original_filename.toLowerCase().includes(q))
    );
  });

  return (
    <div className="dashboard-overview-container animate-fade-in" id="dashboard-overview-root">
      {/* 1. Welcome Hero Section */}
      <section className="dashboard-welcome-hero glass-card" id="dashboard-welcome-banner">
        <div className="welcome-hero-content">
          <div className="welcome-tag-row">
            <span className="pill-badge pill-purple">CodeSage AI v1.0</span>
            <span className="pill-badge pill-success">
              <span className="status-dot-mini connected"></span>
              Live Session
            </span>
          </div>

          <h1 className="welcome-title" id="dashboard-welcome-title">
            Welcome back, {userName} 👋
          </h1>
          <p className="welcome-subtitle">
            Understand, analyze, and explore your software projects with AI.
          </p>
        </div>

        <div className="welcome-hero-actions">
          <Link to="/dashboard/profile" className="btn btn-secondary btn-sm" id="welcome-view-profile-btn">
            <Icon name="profile" size={16} />
            <span>Profile</span>
          </Link>

          <Link to="/dashboard/projects" className="btn btn-primary btn-sm" id="welcome-new-project-btn">
            <Icon name="upload" size={16} />
            <span>+ New Project</span>
          </Link>
        </div>
      </section>

      {/* Overview Metrics Cards Grid (with Skeleton Fallback) */}
      {loadingProjects ? (
        <SkeletonMetric count={4} />
      ) : (
        <section className="overview-metrics-grid" id="dashboard-metrics-section">
          {metrics.map((m) => (
            <div key={m.id} className="card glass-card metric-card" id={m.id}>
              <div className="metric-card-top">
                <div className={`metric-icon-wrap ${m.tagColor}`}>
                  <Icon name={m.icon} size={22} />
                </div>
                <span className={`pill-badge pill-${m.tagColor}`}>{m.tag}</span>
              </div>
              <div className="metric-card-body">
                <div className="metric-number font-mono">{m.value}</div>
                <div className="metric-name">{m.label}</div>
                <p className="metric-sub">{m.description}</p>
              </div>
            </div>
          ))}
        </section>
      )}

      {/* 2. Quick Actions Section ("What can I do?") */}
      <section className="dashboard-quick-actions-section" id="dashboard-quick-actions">
        <div className="section-header-row">
          <div>
            <h2 className="section-title">
              <Icon name="sparkles" size={20} className="text-cyan" />
              <span>Quick Actions</span>
            </h2>
            <p className="section-desc">Instantly jump to common development and understanding tasks</p>
          </div>
        </div>

        <div className="quick-actions-card-grid">
          {quickActions.map((action) => (
            <div key={action.id} className="quick-action-card glass-card" id={action.id}>
              <div className="qa-card-top">
                <div className={`qa-icon-wrap ${action.color}`}>
                  <Icon name={action.icon} size={20} />
                </div>
                <h3 className="qa-card-title">{action.title}</h3>
              </div>

              <p className="qa-card-desc">{action.description}</p>

              <div className="qa-card-footer">
                <Link to={action.to} className="btn btn-secondary btn-sm qa-action-btn">
                  <span>{action.btnText}</span>
                  <Icon name="chevron-right" size={14} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Your Projects Section ("What projects do I have?") */}
      <section className="dashboard-recent-projects glass-card" id="dashboard-projects-section">
        <div className="recent-projects-header">
          <div className="projects-header-left">
            <h2 className="section-title" style={{ margin: 0 }}>
              <Icon name="projects" size={20} />
              <span>Your Projects</span>
            </h2>
            <p className="section-desc" style={{ margin: 0 }}>
              Explore and understand your software projects.
            </p>
          </div>

          <div className="projects-header-right">
            {/* Quick real-time search input */}
            <div className="project-search-filter-wrap">
              <Icon name="search" size={14} className="filter-search-icon" />
              <input
                type="text"
                className="project-filter-input font-mono"
                placeholder="Filter projects..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                id="dashboard-project-filter-input"
              />
              {searchFilter && (
                <button
                  type="button"
                  className="filter-clear-btn"
                  onClick={() => setSearchFilter('')}
                  title="Clear filter"
                >
                  ✕
                </button>
              )}
            </div>

            <Link to="/dashboard/projects" className="btn btn-primary btn-sm" id="projects-upload-new-btn">
              <Icon name="upload" size={14} />
              <span>+ New Project</span>
            </Link>
          </div>
        </div>

        {/* Error Alert with Retry */}
        {fetchError && (
          <div className="auth-alert error animate-fade-in" style={{ margin: '16px 20px' }}>
            <div className="alert-icon-wrap">
              <Icon name="error" size={18} />
            </div>
            <div className="alert-text">
              <strong>Error loading projects:</strong> {fetchError}
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-xs"
              onClick={loadProjects}
              style={{ marginLeft: 'auto' }}
            >
              <Icon name="refresh" size={12} />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Loading Skeleton */}
        {loadingProjects ? (
          <div className="recent-projects-grid">
            <div className="skeleton-card" style={{ height: '140px' }} />
            <div className="skeleton-card" style={{ height: '140px' }} />
            <div className="skeleton-card" style={{ height: '140px' }} />
          </div>
        ) : userProjects.length === 0 ? (
          /* Empty State */
          <div className="empty-projects-state" id="dashboard-empty-projects">
            <div className="empty-icon-wrap">
              <Icon name="folder" size={28} />
            </div>
            <div className="empty-text-wrap">
              <h3 className="empty-state-title">No projects yet</h3>
              <p className="empty-state-desc text-secondary">
                Upload your first software project to explore and understand your code with CodeSage AI.
              </p>
            </div>
            <Link to="/dashboard/projects" className="btn btn-primary btn-sm" id="empty-state-upload-btn">
              <Icon name="upload" size={16} />
              <span>Upload Project</span>
            </Link>
          </div>
        ) : filteredProjects.length === 0 ? (
          /* Filter zero results state */
          <div className="empty-projects-state">
            <p className="text-secondary font-mono">
              No projects matching &ldquo;{searchFilter}&rdquo;
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setSearchFilter('')}
            >
              Clear Filter
            </button>
          </div>
        ) : (
          /* Project Cards Grid */
          <div className="recent-projects-grid" id="dashboard-projects-grid">
            {filteredProjects.map((proj) => (
              <div
                key={proj.id}
                className="recent-project-card glass-card"
                id={`project-card-${proj.id}`}
                onClick={() => handleSetActiveProject(proj)}
              >
                <div className="recent-project-top">
                  <div className="recent-project-icon">
                    <Icon name="folder" size={20} />
                  </div>
                  <div className="recent-project-info">
                    <h3 className="recent-project-name" title={proj.name}>
                      {proj.name}
                    </h3>
                    <div className="recent-project-meta font-mono">
                      <span>{proj.file_count || 0} files</span>
                      <span>&bull;</span>
                      <span className="capitalize text-success font-semibold">
                        {proj.status === 'indexed' || proj.status === 'active' || proj.status === 'ready'
                          ? '✓ Ready'
                          : proj.status || 'Active'}
                      </span>
                    </div>
                  </div>

                  {/* Three-Dot Menu Button */}
                  <div
                    className="project-menu-wrap"
                    onClick={(e) => {
                      e.stopPropagation();
                      setOpenDropdownId(openDropdownId === proj.id ? null : proj.id);
                    }}
                  >
                    <button
                      type="button"
                      className="btn-project-menu"
                      aria-label={`Open menu for ${proj.name}`}
                      id={`project-menu-btn-${proj.id}`}
                    >
                      &#8942;
                    </button>

                    {/* Dropdown Options (Strictly supported existing features only) */}
                    {openDropdownId === proj.id && (
                      <div className="project-dropdown-menu glass-card animate-fade-in" role="menu">
                        <Link
                          to={`/dashboard/projects/${proj.id}/analysis`}
                          className="dropdown-menu-item"
                          onClick={() => handleSetActiveProject(proj)}
                        >
                          <Icon name="analysis" size={14} />
                          <span>Project Overview</span>
                        </Link>
                        <Link
                          to={`/dashboard/projects/${proj.id}/explorer`}
                          className="dropdown-menu-item"
                          onClick={() => handleSetActiveProject(proj)}
                        >
                          <Icon name="code" size={14} />
                          <span>Code Explorer</span>
                        </Link>
                        <Link
                          to={`/dashboard/projects/${proj.id}/dependencies`}
                          className="dropdown-menu-item"
                          onClick={() => handleSetActiveProject(proj)}
                        >
                          <Icon name="dependencies" size={14} />
                          <span>Dependencies</span>
                        </Link>
                        <Link
                          to={`/dashboard/projects/${proj.id}/search`}
                          className="dropdown-menu-item"
                          onClick={() => handleSetActiveProject(proj)}
                        >
                          <Icon name="search" size={14} />
                          <span>Search Code</span>
                        </Link>
                        <Link
                          to={`/dashboard/projects/${proj.id}/chat`}
                          className="dropdown-menu-item"
                          onClick={() => handleSetActiveProject(proj)}
                        >
                          <Icon name="chat" size={14} />
                          <span>Ask AI</span>
                        </Link>
                        <Link
                          to={`/dashboard/projects/${proj.id}/docs`}
                          className="dropdown-menu-item"
                          onClick={() => handleSetActiveProject(proj)}
                        >
                          <Icon name="docs" size={14} />
                          <span>Documentation</span>
                        </Link>
                        <Link
                          to="/dashboard/export"
                          className="dropdown-menu-item"
                          onClick={() => handleSetActiveProject(proj)}
                        >
                          <Icon name="download" size={14} />
                          <span>Export Documentation</span>
                        </Link>
                      </div>
                    )}
                  </div>
                </div>

                <div className="recent-project-date font-mono">
                  <span>Uploaded {proj.created_at ? new Date(proj.created_at).toLocaleDateString() : 'recently'}</span>
                  {proj.original_filename && (
                    <span className="project-archive-badge font-mono" title={proj.original_filename}>
                      {proj.original_filename}
                    </span>
                  )}
                </div>

                <div className="recent-project-actions">
                  <Link
                    to={`/dashboard/projects/${proj.id}/analysis`}
                    className="btn btn-ghost btn-sm"
                    title="View Project Analysis"
                    onClick={() => handleSetActiveProject(proj)}
                    id={`project-analyze-btn-${proj.id}`}
                  >
                    <Icon name="analysis" size={14} />
                    <span>Analyze</span>
                  </Link>

                  <Link
                    to={`/dashboard/projects/${proj.id}/explorer`}
                    className="btn btn-ghost btn-sm"
                    title="Explore Codebase Files"
                    onClick={() => handleSetActiveProject(proj)}
                    id={`project-explore-btn-${proj.id}`}
                  >
                    <Icon name="code" size={14} />
                    <span>Explore</span>
                  </Link>

                  <Link
                    to={`/dashboard/projects/${proj.id}/chat`}
                    className="btn btn-primary btn-sm"
                    title="Ask AI about this codebase"
                    onClick={() => handleSetActiveProject(proj)}
                    id={`project-askai-btn-${proj.id}`}
                  >
                    <Icon name="chat" size={14} />
                    <span>Ask AI</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 4. AI Assistant Showcase ("What should I do next?") */}
      <section className="dashboard-ai-showcase glass-card" id="dashboard-ai-showcase">
        <div className="ai-showcase-header">
          <div className="ai-showcase-icon-box">
            <Icon name="chat" size={22} />
          </div>
          <div>
            <h3 className="ai-showcase-title">AI Assistant &bull; Understand Your Codebase</h3>
            <p className="ai-showcase-sub">
              Ask natural-language questions about your project and receive precise answers with verified source references.
            </p>
          </div>
          <Link to="/dashboard/chat" className="btn btn-primary btn-sm ai-showcase-cta" id="ai-showcase-open-btn">
            <Icon name="chat" size={14} />
            <span>Open AI Chat</span>
          </Link>
        </div>

        <div className="suggested-prompts-grid">
          {suggestedPrompts.map((p, idx) => (
            <Link
              key={idx}
              to="/dashboard/chat"
              className="suggested-prompt-pill glass-card"
              title="Ask this question in AI Assistant"
            >
              <span className="prompt-bullet">&ldquo;</span>
              <span className="prompt-text">{p}</span>
              <Icon name="chevron-right" size={14} className="prompt-arrow" />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}


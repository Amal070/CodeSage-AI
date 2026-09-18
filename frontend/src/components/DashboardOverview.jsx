import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import { SkeletonMetric } from './common/Skeleton';

export default function DashboardOverview() {
  const { user, token, logout, BACKEND_URL } = useAuth();

  const [userProjects, setUserProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(true);

  // Fetch projects to show real counts and recent project list
  useEffect(() => {
    if (!token) return;
    fetch(`${BACKEND_URL}/api/projects`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (res.status === 401) {
          logout();
          return [];
        }
        return res.ok ? res.json() : [];
      })
      .then((data) => setUserProjects(Array.isArray(data) ? data : []))
      .catch(() => setUserProjects([]))
      .finally(() => setLoadingProjects(false));
  }, [token, BACKEND_URL, logout]);

  const totalFiles = userProjects.reduce((acc, p) => acc + (p.file_count || 0), 0);

  // Application-oriented metrics
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

  const userName = user?.name || 'Developer';

  return (
    <div className="dashboard-overview-container animate-fade-in">
      {/* Welcome Hero Area */}
      <section className="dashboard-welcome-hero glass-card">
        <div className="welcome-hero-content">
          <div className="welcome-tag-row">
            <span className="pill-badge pill-purple">CodeSage AI v1.0</span>
            <span className="pill-badge pill-success">
              <span className="status-dot-mini connected"></span>
              Live Session
            </span>
          </div>

          <h1 className="welcome-title" id="dashboard-welcome-title">
            Welcome to CodeSage AI, {userName} 👋
          </h1>
          <p className="welcome-subtitle">
            Understand, analyze, and document your software projects with AI.
          </p>
        </div>

        <div className="welcome-hero-actions">
          <Link to="/dashboard/profile" className="btn btn-secondary btn-sm" id="welcome-view-profile-btn">
            <Icon name="profile" size={16} />
            <span>View Profile</span>
          </Link>

          <Link to="/dashboard/projects" className="btn btn-primary btn-sm" id="welcome-view-projects-btn">
            <Icon name="upload" size={16} />
            <span>Upload Project</span>
          </Link>
        </div>
      </section>

      {/* Quick Status Bar */}
      <div className="overview-status-bar glass-card">
        <div className="status-bar-item">
          <span className="metric-dot connected"></span>
          <div className="status-bar-text">
            <span className="status-bar-label">Platform Status</span>
            <span className="status-bar-value font-mono">Ready</span>
          </div>
        </div>

        <div className="status-bar-item">
          <span className="metric-dot purple"></span>
          <div className="status-bar-text">
            <span className="status-bar-label">Code Search</span>
            <span className="status-bar-value font-mono">Enabled</span>
          </div>
        </div>

        <div className="status-bar-item">
          <span className="metric-dot cyan"></span>
          <div className="status-bar-text">
            <span className="status-bar-label">AI Assistant</span>
            <span className="status-bar-value font-mono">Available</span>
          </div>
        </div>

        <div className="status-bar-item">
          <span className="metric-dot emerald"></span>
          <div className="status-bar-text">
            <span className="status-bar-label">Workspace Session</span>
            <span className="status-bar-value font-mono">Active</span>
          </div>
        </div>
      </div>

      {/* Overview Metrics Cards Grid (with Skeleton Fallback) */}
      {loadingProjects ? (
        <SkeletonMetric count={4} />
      ) : (
        <section className="overview-metrics-grid">
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

      {/* Day 23 Enhancement: Recent Projects Section */}
      <section className="dashboard-recent-projects glass-card" id="dashboard-recent-projects">
        <div className="recent-projects-header">
          <h3>
            <Icon name="projects" size={20} />
            <span>Recent Projects</span>
          </h3>
          <Link to="/dashboard/projects" className="btn btn-secondary btn-sm" id="view-all-projects-btn">
            <span>Upload New</span>
            <Icon name="chevron-right" size={14} />
          </Link>
        </div>

        {loadingProjects ? (
          <div className="recent-projects-grid">
            <div className="skeleton-card" style={{ height: '110px' }} />
            <div className="skeleton-card" style={{ height: '110px' }} />
          </div>
        ) : userProjects.length === 0 ? (
          <div className="empty-projects-state">
            <div className="empty-icon-wrap">
              <Icon name="upload" size={24} />
            </div>
            <div className="empty-text-wrap">
              <h4 className="empty-state-title">No projects uploaded yet</h4>
              <p className="empty-state-desc text-secondary">
                Upload your first codebase archive (ZIP) to unpack, explore code, and chat with AI.
              </p>
            </div>
            <Link to="/dashboard/projects" className="btn btn-primary btn-sm">
              <Icon name="upload" size={16} />
              <span>Upload Project ZIP</span>
            </Link>
          </div>
        ) : (
          <div className="recent-projects-grid">
            {userProjects.slice(0, 6).map((proj) => (
              <div key={proj.id} className="recent-project-card glass-card">
                <div className="recent-project-top">
                  <div className="recent-project-icon">
                    <Icon name="folder" size={20} />
                  </div>
                  <div className="recent-project-info">
                    <h4 className="recent-project-name" title={proj.name}>
                      {proj.name}
                    </h4>
                    <div className="recent-project-meta font-mono">
                      <span>{proj.file_count || 0} files</span>
                      <span>&bull;</span>
                      <span className="capitalize">{proj.status || 'Active'}</span>
                    </div>
                  </div>
                </div>

                <div className="recent-project-actions">
                  <Link
                    to={`/dashboard/projects/${proj.id}/analysis`}
                    className="btn btn-ghost btn-sm"
                    title="View Project Overview"
                  >
                    <Icon name="analysis" size={14} />
                    <span>Analyze Project</span>
                  </Link>

                  <Link
                    to={`/dashboard/projects/${proj.id}/explorer`}
                    className="btn btn-ghost btn-sm"
                    title="Explore Code"
                  >
                    <Icon name="files" size={14} />
                    <span>Explore Code</span>
                  </Link>

                  <Link
                    to={`/dashboard/projects/${proj.id}/chat`}
                    className="btn btn-primary btn-sm"
                    title="Ask AI about codebase"
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

      {/* Two-Column Middle Section: Application Features & Quick Navigation */}
      <div className="overview-split-grid" style={{ marginTop: '24px' }}>
        {/* Application Capabilities Card */}
        <div className="card glass-card host-env-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon cyan">
                <Icon name="sparkles" size={18} />
              </div>
              <div>
                <h3>Application Capabilities</h3>
                <p className="card-desc">What CodeSage AI can do for your software projects</p>
              </div>
            </div>
          </div>

          <div className="quick-actions-list" style={{ marginTop: '12px' }}>
            <Link to="/dashboard/explorer" className="action-row-item">
              <div className="action-row-left">
                <div className="action-icon cyan">
                  <Icon name="code" size={16} />
                </div>
                <div>
                  <h4>Explore &amp; Understand Code</h4>
                  <p>Browse directory trees, inspect source files, and view code structure</p>
                </div>
              </div>
              <Icon name="chevron-right" size={16} />
            </Link>

            <Link to="/dashboard/ai" className="action-row-item">
              <div className="action-row-left">
                <div className="action-icon purple">
                  <Icon name="chat" size={16} />
                </div>
                <div>
                  <h4>Ask AI Assistant</h4>
                  <p>Ask natural-language questions to understand architecture and functions</p>
                </div>
              </div>
              <Icon name="chevron-right" size={16} />
            </Link>

            <Link to="/dashboard/export" className="action-row-item">
              <div className="action-row-left">
                <div className="action-icon emerald">
                  <Icon name="download" size={16} />
                </div>
                <div>
                  <h4>Export Project Documentation</h4>
                  <p>Generate and download comprehensive project guides as Markdown or PDF</p>
                </div>
              </div>
              <Icon name="chevron-right" size={16} />
            </Link>
          </div>
        </div>

        {/* Quick Navigation Panel */}
        <div className="card glass-card quick-actions-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon purple">
                <Icon name="projects" size={18} />
              </div>
              <div>
                <h3>Platform Navigation</h3>
                <p className="card-desc">Quick shortcuts to project workspaces</p>
              </div>
            </div>
          </div>

          <div className="quick-actions-list">
            <Link to="/dashboard/projects" className="action-row-item" id="quick-action-projects">
              <div className="action-row-left">
                <div className="action-icon cyan">
                  <Icon name="upload" size={16} />
                </div>
                <div>
                  <h4>Upload &amp; Manage Projects</h4>
                  <p>Upload new codebase archives and manage existing projects</p>
                </div>
              </div>
              <Icon name="chevron-right" size={16} />
            </Link>

            <Link to="/dashboard/api-docs" className="action-row-item" id="quick-action-api-docs">
              <div className="action-row-left">
                <div className="action-icon emerald">
                  <Icon name="api" size={16} />
                </div>
                <div>
                  <h4>API Documentation</h4>
                  <p>Inspect endpoints, schemas, and generate developer guides</p>
                </div>
              </div>
              <Icon name="chevron-right" size={16} />
            </Link>

            <Link to="/dashboard/settings" className="action-row-item" id="quick-action-settings">
              <div className="action-row-left">
                <div className="action-icon purple">
                  <Icon name="settings" size={16} />
                </div>
                <div>
                  <h4>Settings &amp; Appearance</h4>
                  <p>Customize themes, notifications, and view developer telemetry</p>
                </div>
              </div>
              <Icon name="chevron-right" size={16} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

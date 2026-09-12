import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function DashboardOverview() {
  const { user, token, logout, BACKEND_URL } = useAuth();

  // Diagnostics & live telemetry
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [latency, setLatency] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);
  const [probing, setProbing] = useState(false);
  const [userProjects, setUserProjects] = useState([]);

  // Fetch projects to show real counts
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
      .then((data) => setUserProjects(data))
      .catch(() => {});
  }, [token, BACKEND_URL, logout]);

  const totalFiles = userProjects.reduce((acc, p) => acc + (p.file_count || 0), 0);

  // Metric cards with real Day 5 project data
  const metrics = [
    {
      id: 'metric-projects',
      label: 'Projects',
      value: String(userProjects.length),
      description: 'Active workspaces',
      tag: 'Day 5 Live',
      tagColor: 'cyan',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
        </svg>
      ),
    },
    {
      id: 'metric-files',
      label: 'Files Analyzed',
      value: String(totalFiles),
      description: 'Indexed source files',
      tag: 'Day 5 Live',
      tagColor: 'purple',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
      ),
    },
    {
      id: 'metric-quality',
      label: 'Code Quality',
      value: '--',
      description: 'AST diagnostic score',
      tag: 'Day 6 AST',
      tagColor: 'amber',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
        </svg>
      ),
    },
    {
      id: 'metric-conversations',
      label: 'AI Conversations',
      value: '0',
      description: 'RAG context sessions',
      tag: 'Day 7 RAG',
      tagColor: 'emerald',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      ),
    },
  ];

  const probeBackend = useCallback(async () => {
    setProbing(true);
    const startTime = performance.now();
    try {
      const res = await fetch(`${BACKEND_URL}/api/system-info`);
      const duration = Math.round(performance.now() - startTime);
      setLatency(duration);
      if (res.ok) {
        const data = await res.json();
        setSystemInfo(data);
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('error');
      }
    } catch {
      setConnectionStatus('disconnected');
    } finally {
      setProbing(false);
    }
  }, [BACKEND_URL]);

  useEffect(() => {
    let active = true;
    const initialProbe = async () => {
      const startTime = performance.now();
      try {
        const res = await fetch(`${BACKEND_URL}/api/system-info`);
        const duration = Math.round(performance.now() - startTime);
        if (!active) return;
        setLatency(duration);
        if (res.ok) {
          const data = await res.json();
          if (!active) return;
          setSystemInfo(data);
          setConnectionStatus('connected');
        } else {
          setConnectionStatus('error');
        }
      } catch {
        if (active) setConnectionStatus('disconnected');
      }
    };

    initialProbe();
    const interval = setInterval(probeBackend, 15000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [BACKEND_URL, probeBackend]);

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
            Welcome back, {userName} 👋
          </h1>
          <p className="welcome-subtitle">
            AI-Powered Code Intelligence &amp; Architecture Dashboard. Monitor workspace metrics, inspect runtime telemetry, and review security schemas.
          </p>
        </div>

        <div className="welcome-hero-actions">
          <Link to="/dashboard/profile" className="btn btn-secondary btn-sm" id="welcome-view-profile-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
            <span>View Profile</span>
          </Link>

          <Link to="/dashboard/projects" className="btn btn-primary btn-sm" id="welcome-view-projects-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span>Upload Project</span>
          </Link>
        </div>
      </section>

      {/* Quick Status Bar */}
      <div className="overview-status-bar glass-card">
        <div className="status-bar-item">
          <span className={`metric-dot ${connectionStatus}`}></span>
          <div className="status-bar-text">
            <span className="status-bar-label">Backend Telemetry</span>
            <span className="status-bar-value font-mono capitalize">{connectionStatus}</span>
          </div>
        </div>

        <div className="status-bar-item">
          <span className="metric-dot purple"></span>
          <div className="status-bar-text">
            <span className="status-bar-label">Auth Protocol</span>
            <span className="status-bar-value font-mono">JWT &bull; HS256</span>
          </div>
        </div>

        <div className="status-bar-item">
          <span className="metric-dot cyan"></span>
          <div className="status-bar-text">
            <span className="status-bar-label">Ping Latency</span>
            <span className="status-bar-value font-mono">
              {latency !== null ? `${latency} ms` : '--'}
            </span>
          </div>
        </div>

        <div className="status-bar-item">
          <span className="metric-dot emerald"></span>
          <div className="status-bar-text">
            <span className="status-bar-label">Database</span>
            <span className="status-bar-value font-mono">PostgreSQL</span>
          </div>
        </div>
      </div>

      {/* Overview Metrics Cards Grid (Day 4 UI Placeholders for Day 5+ APIs) */}
      <section className="overview-metrics-grid">
        {metrics.map((m) => (
          <div key={m.id} className="card glass-card metric-card" id={m.id}>
            <div className="metric-card-top">
              <div className={`metric-icon-wrap ${m.tagColor}`}>{m.icon}</div>
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

      {/* Two-Column Middle Section: Host Environment & Quick Actions */}
      <div className="overview-split-grid">
        {/* Host Execution Environment Card */}
        <div className="card glass-card host-env-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon cyan">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
                  <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
                  <line x1="6" y1="6" x2="6.01" y2="6"></line>
                  <line x1="6" y1="18" x2="6.01" y2="18"></line>
                </svg>
              </div>
              <div>
                <h3>Host Runtime Diagnostics</h3>
                <p className="card-desc">Live FastAPI environment telemetry</p>
              </div>
            </div>

            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={probeBackend}
              disabled={probing}
              id="refresh-diagnostics-btn"
              title="Refresh telemetry"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={probing ? 'animate-spin' : ''}>
                <path d="M23 4v6h-6"></path>
                <path d="M1 20v-6h6"></path>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
              <span>{probing ? 'Probing...' : 'Probe'}</span>
            </button>
          </div>

          <div className="env-details-grid">
            <div className="env-item">
              <span className="env-label">Backend Framework</span>
              <span className="env-value font-mono">{systemInfo?.framework || 'FastAPI'}</span>
            </div>
            <div className="env-item">
              <span className="env-label">Python Runtime</span>
              <span className="env-value font-mono">{systemInfo?.python_version || '--'}</span>
            </div>
            <div className="env-item">
              <span className="env-label">Host OS</span>
              <span className="env-value font-mono">{systemInfo?.platform || '--'}</span>
            </div>
            <div className="env-item">
              <span className="env-label">Server Uptime</span>
              <span className="env-value font-mono text-emerald">
                {systemInfo?.uptime_seconds !== undefined
                  ? `${systemInfo.uptime_seconds}s active`
                  : '--'}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Actions Panel */}
        <div className="card glass-card quick-actions-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon purple">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                </svg>
              </div>
              <div>
                <h3>Platform Navigation</h3>
                <p className="card-desc">Quick shortcuts to authenticated features</p>
              </div>
            </div>
          </div>

          <div className="quick-actions-list">
            <Link to="/dashboard/profile" className="action-row-item" id="quick-action-profile">
              <div className="action-row-left">
                <div className="action-icon purple">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                  </svg>
                </div>
                <div>
                  <h4>User Profile &amp; Token Verification</h4>
                  <p>Inspect active JWT session and verify <code>/api/auth/me</code></p>
                </div>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </Link>

            <Link to="/dashboard/security" className="action-row-item" id="quick-action-security">
              <div className="action-row-left">
                <div className="action-icon cyan">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                  </svg>
                </div>
                <div>
                  <h4>Security &amp; Database Architecture</h4>
                  <p>View PostgreSQL schema definitions and bcrypt hashing standards</p>
                </div>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </Link>

            <Link to="/dashboard/projects" className="action-row-item" id="quick-action-projects">
              <div className="action-row-left">
                <div className="action-icon emerald">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                  </svg>
                </div>
                <div>
                  <h4>Project Management Roadmap</h4>
                  <p>Learn about upcoming Day 5 repository ingestion features</p>
                </div>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

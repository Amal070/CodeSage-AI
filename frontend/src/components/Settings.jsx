import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Icon } from './common/Icon';
import ThemeToggle from './common/ThemeToggle';
import { useToast } from './common/Toast';

export default function Settings() {
  const { user, BACKEND_URL } = useAuth();
  const { theme, setTheme } = useTheme();
  const toast = useToast();

  const [activeTab, setActiveTab] = useState('appearance');
  const [notifications, setNotifications] = useState({
    analysisReady: true,
    docReady: true,
    emailSummary: false,
  });

  // Host telemetry for Advanced / Developer section
  const [systemInfo, setSystemInfo] = useState(null);
  const [probing, setProbing] = useState(false);
  const [latency, setLatency] = useState(null);

  const probeBackend = useCallback(async () => {
    setProbing(true);
    const start = performance.now();
    try {
      const res = await fetch(`${BACKEND_URL}/api/system-info`);
      const duration = Math.round(performance.now() - start);
      setLatency(duration);
      if (res.ok) {
        const data = await res.json();
        setSystemInfo(data);
      }
    } catch {
      // ignore
    } finally {
      setProbing(false);
    }
  }, [BACKEND_URL]);

  useEffect(() => {
    if (activeTab === 'advanced') {
      probeBackend();
    }
  }, [activeTab, probeBackend]);

  const handleNotificationToggle = (key) => {
    setNotifications((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      toast.success('Preferences saved');
      return next;
    });
  };

  return (
    <div className="project-analysis-container animate-fade-in" id="settings-page">
      {/* Header Banner */}
      <header className="analysis-header-card glass-card">
        <div className="analysis-header-left">
          <nav className="explorer-breadcrumbs font-mono" aria-label="Breadcrumb">
            <Link to="/dashboard" className="crumb-link">Dashboard</Link>
            <span className="crumb-sep">/</span>
            <span className="crumb-active">Settings</span>
          </nav>

          <div className="project-title-row">
            <div className="project-header-icon">
              <Icon name="settings" size={24} />
            </div>
            <div>
              <h1 className="analysis-project-title">Settings &amp; Preferences</h1>
              <p className="analysis-project-sub text-secondary font-mono">
                Manage your workspace appearance, notifications, and account preferences
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Settings Navigation Tabs */}
      <div className="code-view-tabs" style={{ marginTop: '1.5rem' }}>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'appearance' ? 'active' : ''}`}
          onClick={() => setActiveTab('appearance')}
          id="tab-appearance-btn"
        >
          <Icon name="sparkles" size={14} />
          <span>Appearance</span>
        </button>

        <button
          type="button"
          className={`tab-btn ${activeTab === 'notifications' ? 'active' : ''}`}
          onClick={() => setActiveTab('notifications')}
          id="tab-notifications-btn"
        >
          <Icon name="bell" size={14} />
          <span>Notifications</span>
        </button>

        <button
          type="button"
          className={`tab-btn ${activeTab === 'account' ? 'active' : ''}`}
          onClick={() => setActiveTab('account')}
          id="tab-account-btn"
        >
          <Icon name="profile" size={14} />
          <span>Account</span>
        </button>

        <button
          type="button"
          className={`tab-btn ${activeTab === 'advanced' ? 'active' : ''}`}
          onClick={() => setActiveTab('advanced')}
          id="tab-advanced-btn"
        >
          <Icon name="code" size={14} />
          <span>Advanced / Developer</span>
        </button>
      </div>

      {/* Tab 1: Appearance */}
      {activeTab === 'appearance' && (
        <div className="card glass-card" style={{ marginTop: '1.5rem', padding: '1.75rem' }}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#f8fafc' }}>Interface Theme</h3>
          <p className="text-secondary" style={{ marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            Customize your visual experience with sleek dark mode or radiant light mode.
          </p>

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              type="button"
              className={`btn ${theme === 'dark' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTheme('dark')}
              id="theme-dark-btn"
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Icon name="moon" size={16} />
              <span>Dark Theme {theme === 'dark' && '✓'}</span>
            </button>

            <button
              type="button"
              className={`btn ${theme === 'light' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTheme('light')}
              id="theme-light-btn"
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Icon name="sun" size={16} />
              <span>Light Theme {theme === 'light' && '✓'}</span>
            </button>

            <div style={{ marginLeft: 'auto' }}>
              <ThemeToggle />
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Notifications */}
      {activeTab === 'notifications' && (
        <div className="card glass-card" style={{ marginTop: '1.5rem', padding: '1.75rem' }}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#f8fafc' }}>Notification Preferences</h3>
          <p className="text-secondary" style={{ marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            Configure when and how you receive application alerts.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
              <div>
                <strong style={{ color: '#f8fafc', display: 'block' }}>Project Analysis Alerts</strong>
                <span className="text-secondary" style={{ fontSize: '0.85rem' }}>Notify when project analysis and file indexing complete</span>
              </div>
              <input
                type="checkbox"
                checked={notifications.analysisReady}
                onChange={() => handleNotificationToggle('analysisReady')}
                style={{ width: '18px', height: '18px', accentColor: 'var(--color-primary, #6366f1)', cursor: 'pointer' }}
              />
            </label>

            <div style={{ height: '1px', background: 'rgba(255, 255, 255, 0.08)' }}></div>

            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
              <div>
                <strong style={{ color: '#f8fafc', display: 'block' }}>Documentation Ready Alerts</strong>
                <span className="text-secondary" style={{ fontSize: '0.85rem' }}>Notify when AI documentation is generated and ready for export</span>
              </div>
              <input
                type="checkbox"
                checked={notifications.docReady}
                onChange={() => handleNotificationToggle('docReady')}
                style={{ width: '18px', height: '18px', accentColor: 'var(--color-primary, #6366f1)', cursor: 'pointer' }}
              />
            </label>
          </div>
        </div>
      )}

      {/* Tab 3: Account */}
      {activeTab === 'account' && (
        <div className="card glass-card" style={{ marginTop: '1.5rem', padding: '1.75rem' }}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#f8fafc' }}>Account Information</h3>
          <p className="text-secondary" style={{ marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            Your CodeSage AI account and workspace credentials.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
            <div>
              <span className="text-secondary font-mono text-xs" style={{ textTransform: 'uppercase' }}>Full Name</span>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '1rem', marginTop: '4px' }}>
                {user?.name || 'Developer'}
              </div>
            </div>

            <div>
              <span className="text-secondary font-mono text-xs" style={{ textTransform: 'uppercase' }}>Email Address</span>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '1rem', marginTop: '4px' }}>
                {user?.email || 'user@codesage.ai'}
              </div>
            </div>

            <div>
              <span className="text-secondary font-mono text-xs" style={{ textTransform: 'uppercase' }}>Account Status</span>
              <div style={{ marginTop: '4px' }}>
                <span className="badge badge-success font-mono">Active Workspace</span>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '2rem' }}>
            <Link to="/dashboard/profile" className="btn btn-secondary btn-sm">
              <Icon name="profile" size={14} />
              <span>View Full Profile</span>
            </Link>
          </div>
        </div>
      )}

      {/* Tab 4: Advanced / Developer Settings */}
      {activeTab === 'advanced' && (
        <div className="card glass-card" style={{ marginTop: '1.5rem', padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div>
              <h3 style={{ margin: 0, color: '#f8fafc' }}>Developer &amp; System Diagnostics</h3>
              <p className="text-secondary" style={{ margin: '4px 0 0', fontSize: '0.9rem' }}>
                Technical runtime diagnostics and server telemetry for administrative inspection.
              </p>
            </div>

            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={probeBackend}
              disabled={probing}
              id="probe-developer-btn"
            >
              <Icon name="refresh" size={14} className={probing ? 'animate-spin' : ''} />
              <span>{probing ? 'Probing...' : 'Refresh Telemetry'}</span>
            </button>
          </div>

          <div style={{ marginTop: '1.5rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div className="env-item" style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '12px', borderRadius: '8px' }}>
              <span className="env-label font-mono text-xs text-secondary">Backend Framework</span>
              <span className="env-value font-mono font-bold" style={{ display: 'block', marginTop: '4px', color: '#f8fafc' }}>
                {systemInfo?.framework || 'FastAPI'}
              </span>
            </div>

            <div className="env-item" style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '12px', borderRadius: '8px' }}>
              <span className="env-label font-mono text-xs text-secondary">Python Runtime</span>
              <span className="env-value font-mono font-bold" style={{ display: 'block', marginTop: '4px', color: '#f8fafc' }}>
                {systemInfo?.python_version || '--'}
              </span>
            </div>

            <div className="env-item" style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '12px', borderRadius: '8px' }}>
              <span className="env-label font-mono text-xs text-secondary">Host Platform</span>
              <span className="env-value font-mono font-bold" style={{ display: 'block', marginTop: '4px', color: '#f8fafc' }}>
                {systemInfo?.platform || '--'}
              </span>
            </div>

            <div className="env-item" style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '12px', borderRadius: '8px' }}>
              <span className="env-label font-mono text-xs text-secondary">Ping Latency</span>
              <span className="env-value font-mono font-bold text-emerald" style={{ display: 'block', marginTop: '4px' }}>
                {latency !== null ? `${latency} ms` : '--'}
              </span>
            </div>
          </div>

          <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(15, 23, 42, 0.3)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                System diagnostic logs and schemas are isolated from normal user workflows.
              </span>
              <Link to="/dashboard/security" className="btn btn-secondary btn-sm" style={{ fontSize: '0.75rem' }}>
                View Database Schema
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

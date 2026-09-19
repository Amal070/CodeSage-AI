import { useState } from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import ThemeToggle from './common/ThemeToggle';
import heroImg from '../assets/hero.png';

export default function DashboardLayout() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const { user } = useAuth();
  const location = useLocation();

  // Determine current section title based on route
  const getRouteTitle = () => {
    const path = location.pathname;
    if (path.includes('/projects')) return 'Projects';
    if (path.includes('/explorer')) return 'Code Explorer';
    if (path.includes('/analysis')) return 'Project Analysis';
    if (path.includes('/dependencies')) return 'Dependencies';
    if (path.includes('/docs')) return 'Documentation';
    if (path.includes('/export')) return 'Export';
    if (path.includes('/settings')) return 'Settings';
    if (path.includes('/profile')) return 'Profile';
    if (path.includes('/security')) return 'Security';
    if (path.includes('/api-docs')) return 'API Documentation';
    if (path.includes('/ai')) return 'AI Assistant';
    return 'Dashboard';
  };

  return (
    <div className="dashboard-app-shell">
      {/* Ambient background glow */}
      <div className="gradient-bg">
        <div className="glow-orb g1"></div>
        <div className="glow-orb g2"></div>
        <div className="glow-orb g3"></div>
      </div>

      {/* Mobile Header Bar */}
      <header className="mobile-dashboard-header glass-nav">
        <div className="mobile-header-left">
          <button
            type="button"
            className="hamburger-btn"
            onClick={() => setMobileSidebarOpen(true)}
            aria-label="Open sidebar menu"
            id="mobile-hamburger-btn"
          >
            <Icon name="dashboard" size={20} />
          </button>
          <div className="mobile-header-brand">
            <img src={heroImg} alt="CodeSage AI" className="mobile-brand-logo" />
            <span className="mobile-brand-title">CodeSage AI</span>
            <span className="mobile-section-badge">{getRouteTitle()}</span>
          </div>
        </div>

        <div className="mobile-header-right">
          <ThemeToggle className="mobile-theme-toggle" />
          <div className="mobile-user-avatar" title={user?.name || 'User'}>
            {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
          </div>
        </div>
      </header>

      {/* Mobile Drawer Overlay Backdrop */}
      {mobileSidebarOpen && (
        <div
          className="sidebar-backdrop animate-fade-in"
          onClick={() => setMobileSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main Layout Container */}
      <div className="dashboard-layout-body">
        {/* Sidebar Component */}
        <Sidebar
          isOpen={mobileSidebarOpen}
          onCloseMobile={() => setMobileSidebarOpen(false)}
        />

        {/* Main Content Area */}
        <main className="dashboard-main-content">
          {/* Professional Desktop Header */}
          <header className="desktop-dashboard-header glass-nav" id="desktop-dashboard-header">
            <div className="desktop-header-left">
              <div className="desktop-breadcrumb">
                <span className="breadcrumb-root">CodeSage AI</span>
                <span className="breadcrumb-divider">/</span>
                <span className="breadcrumb-current">{getRouteTitle()}</span>
              </div>
            </div>

            <div className="desktop-header-center">
              <Link to="/dashboard/search" className="header-search-box" id="header-global-search-btn">
                <Icon name="search" size={15} />
                <span className="header-search-placeholder">Search code, symbols, or functions...</span>
                <kbd className="header-search-shortcut font-mono">⌘K</kbd>
              </Link>
            </div>

            <div className="desktop-header-right">
              <div className="header-status-pill" title="Platform and AI Services operational">
                <span className="status-dot-mini connected"></span>
                <span className="font-mono text-xs">Platform Ready</span>
              </div>

              <Link
                to="/dashboard/projects"
                className="btn btn-primary btn-sm header-upload-btn"
                id="header-new-project-btn"
              >
                <Icon name="upload" size={14} />
                <span>+ New Project</span>
              </Link>

              <ThemeToggle className="desktop-theme-toggle" />

              <Link
                to="/dashboard/profile"
                className="desktop-user-profile-pill"
                id="header-profile-link"
                title={`Signed in as ${user?.name || 'User'}`}
              >
                <div className="desktop-user-avatar">
                  {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
                </div>
                <span className="desktop-user-name">{user?.name || 'Profile'}</span>
              </Link>
            </div>
          </header>

          <div className="dashboard-content-inner">
            <Outlet />
          </div>

          {/* Clean Dashboard Footer */}
          <footer className="dashboard-footer">
            <p>CodeSage AI &bull; Intelligent Code Understanding Platform &copy; 2026</p>
            <div className="footer-links-row">
              <span className="footer-dot-pill">All Systems Operational</span>
              <span className="footer-dot-pill">AI Assistant Active</span>
              <span className="footer-dot-pill">Secure Session</span>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

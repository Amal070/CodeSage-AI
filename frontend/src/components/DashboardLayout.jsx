import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuth } from '../context/AuthContext';
import heroImg from '../assets/hero.png';

export default function DashboardLayout() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const { user } = useAuth();
  const location = useLocation();

  // Determine current section title based on route
  const getRouteTitle = () => {
    const path = location.pathname;
    if (path.includes('/projects')) return 'Projects';
    if (path.includes('/profile')) return 'User Profile';
    if (path.includes('/security')) return 'Security & Schema';
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
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          <div className="mobile-header-brand">
            <img src={heroImg} alt="CodeSage AI" className="mobile-brand-logo" />
            <span className="mobile-brand-title">CodeSage AI</span>
            <span className="mobile-section-badge">{getRouteTitle()}</span>
          </div>
        </div>

        <div className="mobile-header-right">
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
          <div className="dashboard-content-inner">
            <Outlet />
          </div>

          {/* Clean Dashboard Footer */}
          <footer className="dashboard-footer">
            <p>CodeSage AI Platform &bull; Day 4 Dashboard &copy; 2026</p>
            <div className="footer-links-row">
              <span className="footer-dot-pill">FastAPI 0.140</span>
              <span className="footer-dot-pill">React 19</span>
              <span className="footer-dot-pill">JWT Bearer HS256</span>
              <span className="footer-dot-pill">PostgreSQL</span>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

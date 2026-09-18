import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import ThemeToggle from './common/ThemeToggle';
import heroImg from '../assets/hero.png';

export default function Sidebar({ isOpen, onCloseMobile }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    if (onCloseMobile) onCloseMobile();
    navigate('/login');
  };

  const navItems = [
    {
      to: '/dashboard',
      label: 'Dashboard',
      end: true,
      iconName: 'dashboard',
    },
    {
      to: '/dashboard/projects',
      label: 'Projects',
      iconName: 'projects',
    },
    {
      to: '/dashboard/explorer',
      label: 'Code Explorer',
      iconName: 'code',
    },
    {
      to: '/dashboard/analysis',
      label: 'Project Analysis',
      iconName: 'analysis',
    },
    {
      to: '/dashboard/dependencies',
      label: 'Dependencies',
      iconName: 'dependencies',
    },
    {
      to: '/dashboard/ai',
      label: 'AI Assistant',
      iconName: 'chat',
    },
    {
      to: '/dashboard/docs',
      label: 'Documentation',
      iconName: 'docs',
    },
    {
      to: '/dashboard/api-docs',
      label: 'API Documentation',
      iconName: 'api',
    },
    {
      to: '/dashboard/export',
      label: 'Export',
      iconName: 'export',
    },
    {
      to: '/dashboard/profile',
      label: 'Profile',
      iconName: 'profile',
    },
    {
      to: '/dashboard/settings',
      label: 'Settings',
      iconName: 'settings',
    },
  ];

  return (
    <aside className={`sidebar-container glass-sidebar ${isOpen ? 'open' : ''}`}>
      {/* Sidebar Header with Brand */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-logo-wrap">
            <img src={heroImg} alt="CodeSage AI" className="sidebar-logo" />
            <span className="sidebar-logo-glow"></span>
          </div>
          <div className="sidebar-brand-text">
            <span className="sidebar-title">CodeSage AI</span>
            <span className="sidebar-subtitle">AI Code Intelligence</span>
          </div>
        </div>

        {/* Mobile Close Button */}
        <button
          type="button"
          className="sidebar-close-btn"
          onClick={onCloseMobile}
          aria-label="Close navigation sidebar"
          id="sidebar-close-btn"
        >
          <Icon name="x" size={20} />
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav" aria-label="Main Navigation">
        <div className="sidebar-nav-section-label">MAIN NAVIGATION</div>
        <ul className="sidebar-nav-list">
          {navItems.map((item) => (
            <li key={item.to} className="sidebar-nav-item">
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? 'active' : ''}`
                }
                onClick={onCloseMobile}
                id={`sidebar-link-${item.label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
              >
                <span className="sidebar-link-icon">
                  <Icon name={item.iconName} size={20} />
                </span>
                <span className="sidebar-link-label">{item.label}</span>
                {item.badge && (
                  <span className="sidebar-link-badge">{item.badge}</span>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Sidebar Footer: User Card + Theme Toggle + Logout */}
      <div className="sidebar-footer">
        <div className="sidebar-user-card glass-card">
          <div className="sidebar-user-avatar">
            {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div className="sidebar-user-details">
            <span className="sidebar-user-name" title={user?.name || 'User'}>
              {user?.name || 'Authenticated User'}
            </span>
            <span className="sidebar-user-email" title={user?.email || ''}>
              {user?.email || 'user@codesage.ai'}
            </span>
          </div>
        </div>

        {/* Day 23: Persistent Theme Toggle */}
        <div className="sidebar-theme-toggle-wrap">
          <ThemeToggle />
        </div>

        <button
          type="button"
          className="sidebar-logout-btn"
          onClick={handleLogout}
          id="sidebar-logout-button"
          title="Sign out of CodeSage AI"
        >
          <Icon name="logout" size={18} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}

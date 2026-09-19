import { useState, useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import ThemeToggle from './common/ThemeToggle';
import heroImg from '../assets/hero.png';

export default function Sidebar({ isOpen, onCloseMobile }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [activeProjectId, setActiveProjectId] = useState(() => {
    return localStorage.getItem('codesage_active_project') || null;
  });
  const [activeProjectName, setActiveProjectName] = useState(() => {
    return localStorage.getItem('codesage_active_project_name') || null;
  });

  // Keep active project in sync with current URL or localStorage
  useEffect(() => {
    const match = location.pathname.match(/\/projects\/(\d+)/);
    if (match && match[1]) {
      const pid = match[1];
      setActiveProjectId(pid);
      localStorage.setItem('codesage_active_project', pid);
    } else {
      const stored = localStorage.getItem('codesage_active_project');
      if (stored) setActiveProjectId(stored);
    }

    const storedName = localStorage.getItem('codesage_active_project_name');
    if (storedName) setActiveProjectName(storedName);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    if (onCloseMobile) onCloseMobile();
    navigate('/login');
  };

  const navSections = [
    {
      id: 'section-platform',
      title: 'PLATFORM',
      items: [
        {
          to: '/dashboard',
          label: 'Dashboard',
          end: true,
          iconName: 'dashboard',
          id: 'sidebar-link-dashboard',
        },
        {
          to: '/dashboard/projects',
          label: 'Projects',
          iconName: 'projects',
          id: 'sidebar-link-projects',
          activeMatch: (pathname) => pathname === '/dashboard/projects' || pathname === '/dashboard/projects/upload',
        },
      ],
    },
    {
      id: 'section-current-project',
      title: 'CURRENT PROJECT',
      badge: activeProjectName,
      items: [
        {
          to: activeProjectId ? `/dashboard/projects/${activeProjectId}/analysis` : '/dashboard/analysis',
          label: 'Project Overview',
          iconName: 'analysis',
          id: 'sidebar-link-project-analysis',
          activeMatch: (pathname) => pathname.includes('/analysis'),
        },
        {
          to: activeProjectId ? `/dashboard/projects/${activeProjectId}/explorer` : '/dashboard/explorer',
          label: 'Code Explorer',
          iconName: 'code',
          id: 'sidebar-link-code-explorer',
          activeMatch: (pathname) => pathname.includes('/explorer'),
        },
        {
          to: activeProjectId ? `/dashboard/projects/${activeProjectId}/dependencies` : '/dashboard/dependencies',
          label: 'Dependencies',
          iconName: 'dependencies',
          id: 'sidebar-link-dependencies',
          activeMatch: (pathname) => pathname.includes('/dependencies'),
        },
      ],
    },
    {
      id: 'section-ai',
      title: 'AI & UNDERSTANDING',
      items: [
        {
          to: activeProjectId ? `/dashboard/projects/${activeProjectId}/search` : '/dashboard/search',
          label: 'Search Code',
          iconName: 'search',
          id: 'sidebar-link-search-code',
          activeMatch: (pathname) => pathname.includes('/search'),
        },
        {
          to: activeProjectId ? `/dashboard/projects/${activeProjectId}/chat` : '/dashboard/ai',
          label: 'AI Assistant',
          iconName: 'chat',
          id: 'sidebar-link-ai-assistant',
          activeMatch: (pathname) =>
            pathname.includes('/chat') ||
            pathname.includes('/rag') ||
            pathname.includes('/ask') ||
            pathname === '/dashboard/ai',
        },
      ],
    },
    {
      id: 'section-documentation',
      title: 'DOCUMENTATION',
      items: [
        {
          to: activeProjectId ? `/dashboard/projects/${activeProjectId}/docs` : '/dashboard/docs',
          label: 'Documentation',
          iconName: 'docs',
          id: 'sidebar-link-documentation',
          activeMatch: (pathname) => pathname.includes('/docs') || pathname.includes('/functions'),
        },
        {
          to: '/dashboard/api-docs',
          label: 'API Documentation',
          iconName: 'api',
          id: 'sidebar-link-api-documentation',
          activeMatch: (pathname) => pathname.includes('/api-docs'),
        },
      ],
    },
    {
      id: 'section-tools',
      title: 'TOOLS',
      items: [
        {
          to: '/dashboard/export',
          label: 'Export Documentation',
          iconName: 'export',
          id: 'sidebar-link-export',
          activeMatch: (pathname) => pathname.includes('/export'),
        },
      ],
    },
    {
      id: 'section-account',
      title: 'ACCOUNT',
      items: [
        {
          to: '/dashboard/profile',
          label: 'Profile',
          iconName: 'profile',
          id: 'sidebar-link-profile',
          activeMatch: (pathname) => pathname.includes('/profile'),
        },
        {
          to: '/dashboard/settings',
          label: 'Settings',
          iconName: 'settings',
          id: 'sidebar-link-settings',
          activeMatch: (pathname) => pathname.includes('/settings'),
        },
      ],
    },
  ];

  const checkIsActive = (item) => {
    if (item.activeMatch) {
      return item.activeMatch(location.pathname);
    }
    if (item.end) {
      return location.pathname === item.to;
    }
    return location.pathname.startsWith(item.to);
  };

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

      {/* Navigation Links Grouped by Section */}
      <nav className="sidebar-nav" aria-label="Main Navigation">
        {navSections.map((section) => (
          <div key={section.id} className="sidebar-section-group">
            <div className="sidebar-nav-section-label">
              <span>{section.title}</span>
              {section.badge && (
                <span className="sidebar-section-badge" title={section.badge}>
                  {section.badge}
                </span>
              )}
            </div>

            <ul className="sidebar-nav-list">
              {section.items.map((item) => {
                const active = checkIsActive(item);
                return (
                  <li key={item.id} className="sidebar-nav-item">
                    <NavLink
                      to={item.to}
                      end={item.end}
                      className={`sidebar-link ${active ? 'active' : ''}`}
                      onClick={onCloseMobile}
                      id={item.id}
                    >
                      <span className="sidebar-link-icon">
                        <Icon name={item.iconName} size={18} />
                      </span>
                      <span className="sidebar-link-label">{item.label}</span>
                      {active && <span className="sidebar-active-dot" aria-hidden="true" />}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
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

        {/* Theme Toggle */}
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

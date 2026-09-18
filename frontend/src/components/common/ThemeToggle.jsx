import { useTheme } from '../../context/ThemeContext';
import { Icon } from './Icon';

export default function ThemeToggle({ variant = 'button', className = '' }) {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();

  if (variant === 'segmented') {
    return (
      <div
        className={`theme-toggle-segmented ${className}`}
        role="group"
        aria-label="Theme selection"
      >
        <button
          type="button"
          className={`theme-seg-btn ${theme === 'light' ? 'active' : ''}`}
          onClick={() => setTheme('light')}
          aria-pressed={theme === 'light'}
          title="Light theme"
          id="theme-btn-light"
        >
          <Icon name="sun" size={14} />
          <span>Light</span>
        </button>
        <button
          type="button"
          className={`theme-seg-btn ${theme === 'dark' ? 'active' : ''}`}
          onClick={() => setTheme('dark')}
          aria-pressed={theme === 'dark'}
          title="Dark theme"
          id="theme-btn-dark"
        >
          <Icon name="moon" size={14} />
          <span>Dark</span>
        </button>
        <button
          type="button"
          className={`theme-seg-btn ${theme === 'system' ? 'active' : ''}`}
          onClick={() => setTheme('system')}
          aria-pressed={theme === 'system'}
          title="Match system theme"
          id="theme-btn-system"
        >
          <Icon name="monitor" size={14} />
          <span>Auto</span>
        </button>
      </div>
    );
  }

  // Compact toggle button (standard for Sidebar and Header)
  const isDark = resolvedTheme === 'dark';

  return (
    <button
      type="button"
      className={`theme-toggle-btn ${className}`}
      onClick={toggleTheme}
      aria-label={`Current theme is ${resolvedTheme}. Click to switch to ${isDark ? 'light' : 'dark'} mode`}
      title={`Switch to ${isDark ? 'Light' : 'Dark'} mode (currently ${resolvedTheme})`}
      id="theme-toggle-button"
    >
      <div className="theme-toggle-icon-wrap">
        {isDark ? (
          <Icon name="sun" size={18} className="theme-icon-sun" />
        ) : (
          <Icon name="moon" size={18} className="theme-icon-moon" />
        )}
      </div>
      <span className="theme-toggle-label">
        {isDark ? 'Light Mode' : 'Dark Mode'}
      </span>
    </button>
  );
}

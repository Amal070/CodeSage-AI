import { Icon } from './Icon';

export default function LoadingState({
  title = 'Loading...',
  message = 'Please wait while CodeSage AI processes your request.',
  progress = null,
  size = 'md',
  className = '',
  id = '',
}) {
  const sizeClass = size === 'sm' ? 'loading-sm' : size === 'lg' ? 'loading-lg' : 'loading-md';

  return (
    <div
      className={`cs-loading-state glass-card ${sizeClass} ${className}`}
      id={id}
      role="status"
      aria-live="polite"
    >
      <div className="cs-loading-spinner-wrap">
        <div className="cs-spinner-ring" />
        <Icon name="sparkles" size={20} className="cs-spinner-core-icon" />
      </div>

      <div className="cs-loading-content">
        <h3 className="cs-loading-title">{title}</h3>
        {message && <p className="cs-loading-message text-secondary">{message}</p>}

        {typeof progress === 'number' && (
          <div className="cs-loading-progress-box">
            <div className="cs-loading-progress-bar">
              <div
                className="cs-loading-progress-fill"
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
              />
            </div>
            <span className="cs-loading-progress-text font-mono">
              {Math.round(progress)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

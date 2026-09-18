/**
 * Reusable Skeleton Loaders for CodeSage AI
 * Matches approximate content shapes for dashboards, trees, code viewer, and cards.
 * Automatically respects prefers-reduced-motion.
 */

export function SkeletonText({ lines = 3, width = '100%', className = '' }) {
  return (
    <div className={`skeleton-text-group ${className}`} aria-busy="true" aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton-line"
          style={{
            width: i === lines - 1 && lines > 1 ? '65%' : width,
          }}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ height = '140px', className = '' }) {
  return (
    <div
      className={`skeleton-card ${className}`}
      style={{ height }}
      aria-busy="true"
      aria-hidden="true"
    >
      <div className="skeleton-card-header">
        <div className="skeleton-avatar" />
        <div className="skeleton-line" style={{ width: '40%' }} />
      </div>
      <div className="skeleton-line" style={{ width: '80%', marginTop: '12px' }} />
      <div className="skeleton-line" style={{ width: '60%', marginTop: '8px' }} />
    </div>
  );
}

export function SkeletonMetric({ count = 4, className = '' }) {
  return (
    <div className={`skeleton-metric-grid ${className}`} aria-busy="true" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-metric-card glass-card">
          <div className="skeleton-metric-top">
            <div className="skeleton-icon-box" />
            <div className="skeleton-pill" />
          </div>
          <div className="skeleton-metric-num" />
          <div className="skeleton-line" style={{ width: '50%', marginTop: '6px' }} />
          <div className="skeleton-line" style={{ width: '75%', marginTop: '4px' }} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTree({ items = 8, className = '' }) {
  return (
    <div className={`skeleton-tree-container ${className}`} aria-busy="true" aria-hidden="true">
      {Array.from({ length: items }).map((_, i) => {
        const indent = (i % 3) * 16 + 8;
        const width = 45 + ((i * 17) % 45);
        return (
          <div
            key={i}
            className="skeleton-tree-row"
            style={{ paddingLeft: `${indent}px` }}
          >
            <div className="skeleton-tree-icon" />
            <div className="skeleton-line" style={{ width: `${width}%` }} />
          </div>
        );
      })}
    </div>
  );
}

export function SkeletonCode({ lines = 12, className = '' }) {
  return (
    <div className={`skeleton-code-container ${className}`} aria-busy="true" aria-hidden="true">
      <div className="skeleton-code-header">
        <div className="skeleton-code-dots">
          <span />
          <span />
          <span />
        </div>
        <div className="skeleton-line" style={{ width: '120px' }} />
      </div>
      <div className="skeleton-code-body">
        {Array.from({ length: lines }).map((_, i) => {
          const indent = (i % 4 === 1 || i % 4 === 2) ? 24 : (i % 4 === 3) ? 48 : 0;
          const widths = [60, 45, 80, 35, 70, 55, 90, 40, 65, 50, 75, 30];
          return (
            <div key={i} className="skeleton-code-line">
              <span className="skeleton-line-num font-mono">{i + 1}</span>
              <div
                className="skeleton-line"
                style={{
                  width: `${widths[i % widths.length]}%`,
                  marginLeft: `${indent}px`,
                }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4, className = '' }) {
  return (
    <div className={`skeleton-table-wrap ${className}`} aria-busy="true" aria-hidden="true">
      <div className="skeleton-table-header">
        {Array.from({ length: cols }).map((_, c) => (
          <div key={c} className="skeleton-line" style={{ width: '60%' }} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="skeleton-table-row">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="skeleton-line" style={{ width: `${50 + ((r + c) * 11) % 40}%` }} />
          ))}
        </div>
      ))}
    </div>
  );
}

export default {
  Text: SkeletonText,
  Card: SkeletonCard,
  Metric: SkeletonMetric,
  Tree: SkeletonTree,
  Code: SkeletonCode,
  Table: SkeletonTable,
};

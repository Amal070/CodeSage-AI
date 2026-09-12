import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * ProtectedRoute Component
 * Concept:
 *   User visits protected page (/dashboard, /profile, etc.)
 *           ↓
 *      JWT exists?
 *     ┌────┴────┐
 *     │         │
 *    YES        NO
 *     │         │
 *     ↓         ↓
 *   Allow      Redirect to /login
 */
export default function ProtectedRoute({ children, fallbackToCard = false }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="protected-loading-view animate-fade-in">
        <div className="glass-card loading-card">
          <span className="spinner large"></span>
          <p>Loading dashboard...</p>
          <span className="loading-sub">Verifying secure session credentials...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (fallbackToCard) {
      return (
        <div className="protected-fallback-view animate-fade-in">
          <div className="glass-card fallback-card">
            <div className="fallback-icon-wrap">
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <h2>Authentication Required</h2>
            <p>
              You must be signed in with a valid JWT token to access protected CodeSage AI
              telemetry and dashboard features.
            </p>
            <Navigate to="/login" replace state={{ from: location }} />
          </div>
        </div>
      );
    }

    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}

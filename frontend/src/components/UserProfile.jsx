import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import { useToast } from './common/Toast';

export default function UserProfile() {
  const { user, token, authFetch } = useAuth();
  const toast = useToast();
  const [refreshedProfile, setRefreshedProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);
  const [currentTime, setCurrentTime] = useState(() => Math.floor(Date.now() / 1000));

  const profileData = refreshedProfile || user;

  // Track time periodically for token countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(Math.floor(Date.now() / 1000));
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  // Decode JWT payload safely in browser for diagnostic inspection using useMemo
  const decodedPayload = useMemo(() => {
    if (!token) return null;
    try {
      const base64Url = token.split('.')[1];
      if (base64Url) {
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
          atob(base64)
            .split('')
            .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
            .join('')
        );
        return JSON.parse(jsonPayload);
      }
    } catch (e) {
      console.error('Failed to parse token payload:', e);
    }
    return null;
  }, [token]);

  // Fetch current user from /api/auth/me
  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const res = await authFetch('/api/auth/me');
      const duration = Math.round(performance.now() - start);
      const data = await res.json();
      if (res.ok) {
        setRefreshedProfile(data);
        setTestResult({
          status: res.status,
          statusText: res.statusText,
          success: true,
          duration,
          data,
          timestamp: new Date().toLocaleTimeString(),
        });
      } else {
        setError(data.detail || 'Failed to retrieve profile information.');
        setTestResult({
          status: res.status,
          statusText: res.statusText,
          success: false,
          duration,
          data,
          timestamp: new Date().toLocaleTimeString(),
        });
      }
    } catch (err) {
      setError(err.message || 'Network error occurred while fetching profile.');
      setTestResult({
        status: 'Error',
        statusText: 'Network Error',
        success: false,
        duration: null,
        data: { error: err.message },
        timestamp: new Date().toLocaleTimeString(),
      });
    } finally {
      setLoading(false);
    }
  };

  const copyToken = () => {
    if (token) {
      navigator.clipboard.writeText(token);
      setCopied(true);
      toast.success('JWT token copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatExpiresIn = (exp) => {
    if (!exp) return 'Unknown';
    const remaining = exp - currentTime;
    if (remaining <= 0) return 'Expired';
    const mins = Math.floor(remaining / 60);
    return `${mins} minutes remaining`;
  };

  return (
    <div className="profile-container animate-fade-in">
      {/* Quick Identity Bar */}
      <div className="profile-hero-banner glass-card">
        <div className="profile-hero-left">
          <div className="user-avatar-large">
            {profileData?.name ? profileData.name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div className="profile-hero-info">
            <div className="name-badge-row">
              <h2 className="user-name-title">{profileData?.name || 'Loading Profile...'}</h2>
              <span className="pill-badge pill-success">Active Session</span>
              <span className="pill-badge pill-purple">Verified User</span>
            </div>
            <p className="user-email-subtitle">{profileData?.email || 'Loading...'}</p>
          </div>
        </div>

        <div className="profile-hero-right">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={fetchProfile}
            disabled={loading}
            id="refresh-profile-btn"
          >
            {loading ? (
              <span className="btn-loading-content">
                <span className="spinner"></span> Refreshing...
              </span>
            ) : (
              <span className="btn-content">
                <Icon name="refresh" size={14} />
                <span>Refresh Profile</span>
              </span>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="auth-alert error animate-shake" role="alert">
          <div className="alert-icon-wrap">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <div className="alert-text">{error}</div>
        </div>
      )}

      <div className="profile-grid">
        {/* User Identity Details Card */}
        <div className="card glass-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon purple">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
              </div>
              <div>
                <h3>Account Profile</h3>
                <p className="card-desc">Personal account information</p>
              </div>
            </div>
            <span className="badge badge-success">Active</span>
          </div>

          <div className="profile-field-list">
            <div className="field-item">
              <span className="field-label">Account ID</span>
              <span className="field-value font-mono" id="profile-user-id">#{profileData?.id || '--'}</span>
            </div>
            <div className="field-item">
              <span className="field-label">Full Name</span>
              <span className="field-value font-medium" id="profile-user-name">{profileData?.name || '--'}</span>
            </div>
            <div className="field-item">
              <span className="field-label">Email Address</span>
              <span className="field-value font-medium" id="profile-user-email">{profileData?.email || '--'}</span>
            </div>
            <div className="field-item">
              <span className="field-label">Member Since</span>
              <span className="field-value font-mono">
                {profileData?.created_at
                  ? new Date(profileData.created_at).toLocaleDateString()
                  : '--'}
              </span>
            </div>
            <div className="field-item">
              <span className="field-label">Account Status</span>
              <span className="field-value text-emerald">Active &amp; Verified</span>
            </div>
          </div>
        </div>

        {/* Session & Security Card */}
        <div className="card glass-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon cyan">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
              </div>
              <div>
                <h3>Session &amp; Security</h3>
                <p className="card-desc">Authentication and security status</p>
              </div>
            </div>
            <span className="badge badge-success">Encrypted</span>
          </div>

          <div className="profile-field-list">
            <div className="field-item">
              <span className="field-label">Session Status</span>
              <span className="field-value text-emerald font-medium">Active</span>
            </div>
            <div className="field-item">
              <span className="field-label">Session Duration</span>
              <span className="field-value font-mono text-emerald">
                {decodedPayload ? formatExpiresIn(decodedPayload.exp) : 'Active'}
              </span>
            </div>
            <div className="field-item">
              <span className="field-label">Security Protocol</span>
              <span className="field-value">Standard Secure Authentication</span>
            </div>
          </div>

          {/* Developer / Advanced Token Details (Collapsible) */}
          <details style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color, rgba(255,255,255,0.08))' }}>
            <summary style={{ cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary, #94a3b8)', userSelect: 'none' }}>
              Advanced / Developer Token Details
            </summary>
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.5rem' }}>
                <button
                  type="button"
                  className={`btn-copy ${copied ? 'copied' : ''}`}
                  onClick={copyToken}
                  id="copy-token-btn"
                >
                  {copied ? '✓ Copied' : 'Copy Token'}
                </button>
              </div>
              <div className="token-code-box">
                <pre className="token-raw-string">
                  <code>{token || 'No active token'}</code>
                </pre>
              </div>
            </div>
          </details>
        </div>
      </div>

      {/* Live API Tester / Inspector (Developer Diagnostics) */}
      {testResult && (
        <details style={{ marginTop: '1.5rem' }}>
          <summary style={{ cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary, #94a3b8)', userSelect: 'none' }}>
            Advanced / Developer Diagnostics
          </summary>
          <div className="card glass-card live-result-card animate-fade-in" style={{ marginTop: '0.75rem' }}>
            <div className="card-header">
              <div className="card-title-group">
                <div className={`card-icon ${testResult.success ? 'emerald' : 'rose'}`}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                  </svg>
                </div>
                <div>
                  <h3>Session Diagnostics — <code>GET /api/auth/me</code></h3>
                  <p className="card-desc">Verified with backend authentication service</p>
                </div>
              </div>
              <div className="result-header-badges">
                {testResult.duration !== null && (
                  <span className="latency-badge">{testResult.duration}ms</span>
                )}
                <span className={`status-pill ${testResult.success ? 'success' : 'error'}`}>
                  HTTP {testResult.status} {testResult.statusText}
                </span>
              </div>
            </div>

            <div className="terminal-window">
              <div className="terminal-header">
                <div className="term-dots">
                  <span className="term-dot red"></span>
                  <span className="term-dot yellow"></span>
                  <span className="term-dot green"></span>
                </div>
                <span className="term-title">
                  Response Payload &bull; {testResult.timestamp}
                </span>
              </div>
              <pre className="terminal-content">
                <code>{JSON.stringify(testResult.data, null, 2)}</code>
              </pre>
            </div>
          </div>
        </details>
      )}
    </div>
  );
}

import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import heroImg from '../assets/hero.png';

export default function LandingPage() {
  const { isAuthenticated, BACKEND_URL } = useAuth();
  const navigate = useNavigate();

  // If already authenticated, redirect to /dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [latency, setLatency] = useState(null);
  const [loading, setLoading] = useState(false);

  const checkConnection = useCallback(async (endpoint = '/api/system-info') => {
    setLoading(true);
    const startTime = performance.now();
    try {
      const response = await fetch(`${BACKEND_URL}${endpoint}`);
      const duration = Math.round(performance.now() - startTime);
      setLatency(duration);

      if (response.ok) {
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('error');
      }
    } catch {
      setConnectionStatus('disconnected');
      setLatency(null);
    } finally {
      setLoading(false);
    }
  }, [BACKEND_URL]);

  useEffect(() => {
    let active = true;
    const initialProbe = async () => {
      const startTime = performance.now();
      try {
        const response = await fetch(`${BACKEND_URL}/api/system-info`);
        const duration = Math.round(performance.now() - startTime);
        if (!active) return;
        setLatency(duration);
        if (response.ok) {
          setConnectionStatus('connected');
        } else {
          setConnectionStatus('error');
        }
      } catch {
        if (active) setConnectionStatus('disconnected');
      }
    };

    initialProbe();
    const interval = setInterval(() => {
      checkConnection('/health');
    }, 10000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [BACKEND_URL, checkConnection]);

  return (
    <div className="dashboard-container">
      {/* Background ambient lighting effects */}
      <div className="gradient-bg">
        <div className="glow-orb g1"></div>
        <div className="glow-orb g2"></div>
        <div className="glow-orb g3"></div>
      </div>

      {/* Main Top Navigation Header */}
      <header className="header glass-nav">
        <div className="logo-group clickable-logo" onClick={() => navigate('/')} role="button" tabIndex={0}>
          <div className="logo-img-wrap">
            <img src={heroImg} className="logo-hero" alt="CodeSage AI" />
            <span className="logo-glow"></span>
          </div>
          <div>
            <div className="brand-title-row">
              <h1>CodeSage AI</h1>
              <span className="version-pill">v1.0.0</span>
            </div>
            <p className="subtitle">AI-Powered Code Intelligence &amp; Diagnostics Platform</p>
          </div>
        </div>

        <div className="header-right">
          <div className="auth-tabs header-auth-tabs">
            <Link to="/login" className="auth-tab-btn" id="header-nav-login">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
                <polyline points="10 17 15 12 10 7"></polyline>
                <line x1="15" y1="12" x2="3" y2="12"></line>
              </svg>
              <span>Login</span>
            </Link>
            <Link to="/register" className="auth-tab-btn active" id="header-nav-register">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="8.5" cy="7" r="4"></circle>
                <line x1="20" y1="8" x2="20" y2="14"></line>
                <line x1="23" y1="11" x2="17" y2="11"></line>
              </svg>
              <span>Register</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="landing-main-view animate-fade-in">
        <section className="landing-hero-section">
          <div className="landing-badge">
            <span className="sparkle-icon">✨</span>
            <span>Next-Gen DevSecOps &amp; Code Intelligence</span>
          </div>
          <h1 className="landing-hero-title">
            Secure Code Intelligence &amp; <span className="title-gradient">Diagnostic Platform</span>
          </h1>
          <p className="landing-hero-description">
            A high-performance environment built with FastAPI dependency injection, cryptographic JWT bearer tokens, and PostgreSQL schema versioning. Monitor performance telemetry, query protected endpoints, and safeguard your engineering workflows.
          </p>

          <div className="landing-actions-group">
            <Link to="/register" className="btn btn-primary btn-hero-cta" id="hero-get-started-btn">
              <span>Register Free Account</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </Link>

            <Link to="/login" className="btn btn-secondary btn-hero-secondary" id="hero-sign-in-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
                <polyline points="10 17 15 12 10 7"></polyline>
                <line x1="15" y1="12" x2="3" y2="12"></line>
              </svg>
              <span>Sign In / Login</span>
            </Link>

            <button
              type="button"
              className="btn btn-ghost btn-hero-probe"
              onClick={() => checkConnection('/api/system-info')}
              disabled={loading}
              id="hero-probe-btn"
              title="Check live API status"
            >
              <span className={`status-dot-mini ${connectionStatus}`}></span>
              <span>{loading ? 'Probing...' : 'Probe Live API'}</span>
            </button>
          </div>
        </section>

        {/* Feature Highlights Grid */}
        <section className="landing-features-grid">
          <div className="landing-feature-card glass-card">
            <div className="feature-card-header">
              <div className="feature-icon-wrap bg-purple">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <span className="feature-tag">Day 3 Security</span>
            </div>
            <h3>JWT Dependency Injection</h3>
            <p>HMAC-SHA256 bearer tokens guarding FastAPI routers with automatic payload verification and token expiry handling.</p>
          </div>

          <div className="landing-feature-card glass-card">
            <div className="feature-card-header">
              <div className="feature-icon-wrap bg-cyan">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                  <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                  <line x1="6" y1="6" x2="6.01" y2="6" />
                  <line x1="6" y1="18" x2="6.01" y2="18" />
                </svg>
              </div>
              <span className="feature-tag">Real-Time</span>
            </div>
            <h3>Diagnostic Telemetry</h3>
            <p>Live WebSocket and HTTP telemetry probes tracking database connection pools and sub-millisecond response latency.</p>
          </div>

          <div className="landing-feature-card glass-card">
            <div className="feature-card-header">
              <div className="feature-icon-wrap bg-indigo">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <span className="feature-tag">PostgreSQL</span>
            </div>
            <h3>Alembic Schema Safety</h3>
            <p>Relational database integrity managed through versioned migrations with zero plaintext password persistence.</p>
          </div>
        </section>

        {/* Live Interactive Telemetry Showcase Card */}
        <section className="landing-preview-section">
          <div className="mock-dashboard-preview glass-card landing-preview-card">
            <div className="mock-header">
              <div className="mock-dots">
                <span className="dot red"></span>
                <span className="dot yellow"></span>
                <span className="dot green"></span>
              </div>
              <div className="mock-address-bar">codesage-ai-api.local/health</div>
              <div className="mock-badge-live">
                {connectionStatus === 'connected' ? 'Backend Live & Healthy' : 'Backend Telemetry Active'}
              </div>
            </div>
            <div className="mock-body">
              <div className="mock-stats-grid">
                <div className="mock-stat-box">
                  <span className="stat-label">ROUNDTRIP PING</span>
                  <span className="stat-val text-green">{latency !== null ? `${latency}ms` : '12ms'}</span>
                  <span className="stat-trend">&darr; Active Connection</span>
                </div>
                <div className="mock-stat-box">
                  <span className="stat-label">DB ENGINE</span>
                  <span className="stat-val text-cyan">PostgreSQL</span>
                  <span className="stat-trend text-glow">codesage_db</span>
                </div>
                <div className="mock-stat-box">
                  <span className="stat-label">AUTH PROTOCOL</span>
                  <span className="stat-val text-purple font-mono">JWT &bull; HS256</span>
                  <span className="stat-trend">Bcrypt Salted</span>
                </div>
              </div>
              <div className="mock-graph-area">
                <div className="graph-y-axis">
                  <span>100ms</span>
                  <span>50ms</span>
                  <span>0ms</span>
                </div>
                <div className="graph-visual">
                  <svg viewBox="0 0 300 80" className="sparkline-svg">
                    <defs>
                      <linearGradient id="sparkline-grad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                      </linearGradient>
                      <linearGradient id="sparkline-grad-stroke" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#a855f7" />
                        <stop offset="100%" stopColor="#06b6d4" />
                      </linearGradient>
                    </defs>
                    <path
                      d="M 0 50 Q 30 20 60 45 T 120 15 T 180 35 T 240 10 T 300 25"
                      fill="none"
                      stroke="url(#sparkline-grad-stroke)"
                      strokeWidth="2.5"
                    />
                    <path
                      d="M 0 50 Q 30 20 60 45 T 120 15 T 180 35 T 240 10 T 300 25 L 300 80 L 0 80 Z"
                      fill="url(#sparkline-grad)"
                    />
                    <circle cx="240" cy="10" r="4" fill="#06b6d4" className="glowing-node-graph" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Quick Action Footer Strip */}
        <section className="landing-cta-banner glass-card">
          <div className="cta-banner-content">
            <div>
              <h2>Ready to inspect and analyze your codebase?</h2>
              <p>Register an account now or sign in to access your secure developer workspace.</p>
            </div>
            <div className="cta-banner-buttons">
              <Link to="/register" className="btn btn-primary" id="cta-register-btn">
                Register Now
              </Link>
              <Link to="/login" className="btn btn-secondary" id="cta-login-btn">
                Login
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="footer glass-footer">
        <div className="footer-content">
          <p className="footer-brand">CodeSage AI Platform &copy; 2026</p>
          <div className="footer-tags">
            <span className="footer-tag">FastAPI</span>
            <span className="footer-tag">React 19</span>
            <span className="footer-tag">PostgreSQL</span>
            <span className="footer-tag">JWT Bearer</span>
            <span className="footer-tag">Bcrypt</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

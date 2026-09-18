import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import heroImg from '../assets/hero.png';
import CodeSage3DHero from './CodeSage3DHero';
import Card3DTilt from './common/Card3DTilt';

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  // If already authenticated, redirect to /dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

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
        <section className="landing-hero-section landing-hero-grid">
          <div className="hero-content-col">
            <div className="landing-badge">
              <span className="sparkle-icon">✨</span>
              <span>Intelligent Code Understanding Platform</span>
            </div>
            <h1 className="landing-hero-title">
              Understand Your Code. <span className="title-gradient">Faster.</span>
            </h1>
            <p className="landing-hero-description">
              AI-powered code understanding for your software projects. Explore project structure, ask questions about your codebase, search code intelligently, and generate documentation in seconds.
            </p>

            <div className="landing-actions-group">
              <Link to="/register" className="btn btn-primary btn-hero-cta" id="hero-get-started-btn">
                <span>Get Started</span>
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
                <span>Sign In</span>
              </Link>
            </div>
          </div>

          <div className="hero-3d-col">
            <CodeSage3DHero />
          </div>
        </section>

        {/* Feature Highlights Grid per Section 22 with 3D Tilt */}
        <section className="landing-features-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
          <Card3DTilt maxTilt={8} scale={1.02} className="tilt-feature-wrapper">
            <div className="landing-feature-card glass-card">
              <div className="feature-card-header">
                <div className="feature-icon-wrap bg-purple">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                </div>
                <span className="feature-tag">AI Assistant</span>
              </div>
              <h3>Understand Code</h3>
              <p>Ask AI questions about your project and understand your software architecture and functions faster.</p>
            </div>
          </Card3DTilt>

          <Card3DTilt maxTilt={8} scale={1.02} className="tilt-feature-wrapper">
            <div className="landing-feature-card glass-card">
              <div className="feature-card-header">
                <div className="feature-icon-wrap bg-cyan">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="20" x2="18" y2="10"></line>
                    <line x1="12" y1="20" x2="12" y2="4"></line>
                    <line x1="6" y1="20" x2="6" y2="14"></line>
                  </svg>
                </div>
                <span className="feature-tag">Overview</span>
              </div>
              <h3>Analyze Projects</h3>
              <p>Get a clear overview of your software project structure, languages, folders, and statistics.</p>
            </div>
          </Card3DTilt>

          <Card3DTilt maxTilt={8} scale={1.02} className="tilt-feature-wrapper">
            <div className="landing-feature-card glass-card">
              <div className="feature-card-header">
                <div className="feature-icon-wrap bg-indigo">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                </div>
                <span className="feature-tag">Fast Search</span>
              </div>
              <h3>Search Code</h3>
              <p>Find relevant code quickly using natural language queries across all files in your project.</p>
            </div>
          </Card3DTilt>

          <Card3DTilt maxTilt={8} scale={1.02} className="tilt-feature-wrapper">
            <div className="landing-feature-card glass-card">
              <div className="feature-card-header">
                <div className="feature-icon-wrap bg-emerald">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                </div>
                <span className="feature-tag">Automation</span>
              </div>
              <h3>Generate Documentation</h3>
              <p>Create useful documentation automatically for functions, classes, and REST API endpoints.</p>
            </div>
          </Card3DTilt>

          <Card3DTilt maxTilt={8} scale={1.02} className="tilt-feature-wrapper">
            <div className="landing-feature-card glass-card">
              <div className="feature-card-header">
                <div className="feature-icon-wrap bg-amber">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                </div>
                <span className="feature-tag">Export</span>
              </div>
              <h3>Export Documentation</h3>
              <p>Download project documentation and API references seamlessly as Markdown or PDF files.</p>
            </div>
          </Card3DTilt>
        </section>

        {/* Live Interactive Application Preview Showcase Card with 3D Depth */}
        <section className="landing-preview-section">
          <Card3DTilt maxTilt={5} scale={1.01} className="tilt-preview-wrapper">
            <div className="mock-dashboard-preview glass-card landing-preview-card">
              <div className="mock-header">
                <div className="mock-dots">
                  <span className="dot red"></span>
                  <span className="dot yellow"></span>
                  <span className="dot green"></span>
                </div>
                <div className="mock-address-bar">codesage-ai.app/workspace</div>
                <div className="mock-badge-live">
                  CodeSage AI Workspace Ready
                </div>
              </div>
              <div className="mock-body">
                <div className="mock-stats-grid">
                  <div className="mock-stat-box">
                    <span className="stat-label">EXPLORE CODE</span>
                    <span className="stat-val text-green">Interactive</span>
                    <span className="stat-trend">&darr; Code Explorer Ready</span>
                  </div>
                  <div className="mock-stat-box">
                    <span className="stat-label">AI ASSISTANT</span>
                    <span className="stat-val text-cyan">Active</span>
                    <span className="stat-trend text-glow">Natural Language Q&amp;A</span>
                  </div>
                  <div className="mock-stat-box">
                    <span className="stat-label">DOCUMENTATION</span>
                    <span className="stat-val text-purple font-mono">Auto-Gen</span>
                    <span className="stat-trend">Markdown &bull; PDF</span>
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
          </Card3DTilt>
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

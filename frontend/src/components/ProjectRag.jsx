import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProjectRag() {
  const { projectId } = useParams();
  const { token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();

  // State
  const [question, setQuestion] = useState('');
  const [topK, setTopK] = useState(5);
  const [asking, setAsking] = useState(false);
  const [ragResult, setRagResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  // Project details & Index status
  const [projectName, setProjectName] = useState('');
  const [indexStatus, setIndexStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(true);

  const answerRef = useRef(null);

  // Curated sample queries for CodeSage RAG
  const sampleQueries = [
    'Where is JWT authentication implemented?',
    'Where is the database connection configured?',
    'Where are uploaded ZIP files extracted?',
    'Which functions handle password hashing or verification?',
    'What Kubernetes deployment configuration exists?',
  ];

  // 1. Fetch Project Details
  const fetchProject = useCallback(async () => {
    if (!token || !projectId) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setProjectName(data.name || `Project #${projectId}`);
      }
    } catch {
      // ignore
    }
  }, [BACKEND_URL, projectId, token, logout, navigate]);

  // 2. Fetch Vector Index Status
  const fetchIndexStatus = useCallback(async () => {
    if (!token || !projectId) return;
    setLoadingStatus(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/vector-index/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setIndexStatus(data);
      }
    } catch {
      // ignore
    } finally {
      setLoadingStatus(false);
    }
  }, [BACKEND_URL, projectId, token, logout, navigate]);

  useEffect(() => {
    fetchProject();
    fetchIndexStatus();
  }, [fetchProject, fetchIndexStatus]);

  // 3. Execute RAG Question Pipeline
  const handleAsk = async (queryText = null) => {
    const q = (queryText !== null ? queryText : question).trim();
    if (!q || asking) return;

    setAsking(true);
    setError(null);
    setRagResult(null);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/rag`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: q,
          top_k: Number(topK),
        }),
      });

      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || 'CodeSage AI failed to generate an answer.');
      }

      setRagResult(data);

      // Smooth scroll to answer
      setTimeout(() => {
        if (answerRef.current) {
          answerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    } catch (err) {
      setError(err.message || 'The AI assistant is currently unavailable. Please try again later.');
    } finally {
      setAsking(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  const handleCopyAnswer = () => {
    if (!ragResult?.answer) return;
    navigator.clipboard.writeText(ragResult.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="project-analysis-container">
      {/* Header card with breadcrumbs and actions */}
      <header className="analysis-header-card glass-card">
        <div className="header-left">
          <nav className="breadcrumb-nav" aria-label="Breadcrumb">
            <Link to="/dashboard" className="breadcrumb-item">Dashboard</Link>
            <span className="breadcrumb-separator">/</span>
            <Link to="/dashboard/projects" className="breadcrumb-item">Projects</Link>
            <span className="breadcrumb-separator">/</span>
            <Link to={`/dashboard/projects/${projectId}`} className="breadcrumb-item">
              {projectName || `Project #${projectId}`}
            </Link>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-current">AI Assistant</span>
          </nav>
          <div className="title-row" style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h1 className="project-title" style={{ margin: 0 }}>
              AI Assistant
            </h1>
          </div>
          <p className="project-subtitle" style={{ margin: '0.25rem 0 0 0', color: 'var(--text-secondary, #94a3b8)' }}>
            Ask questions about your project and understand your code faster.
          </p>
        </div>

        <div className="header-actions">
          <Link
            to={`/dashboard/projects/${projectId}`}
            className="btn btn-secondary btn-sm"
            id="back-to-analysis-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            <span>Analysis</span>
          </Link>
          <Link
            to={`/dashboard/projects/${projectId}/search`}
            className="btn btn-secondary btn-sm"
            id="nav-search-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <span>Search Code</span>
          </Link>
          <Link
            to={`/dashboard/projects/${projectId}/chat`}
            className="btn btn-primary btn-sm"
            id="nav-chat-btn"
            style={{
              background: 'linear-gradient(135deg, #9333ea, #6366f1)',
              borderColor: '#a855f7',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>AI Chat</span>
          </Link>
          <Link
            to={`/dashboard/projects/${projectId}/explorer`}
            className="btn btn-primary btn-sm"
            id="nav-explorer-btn"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"></polyline>
              <polyline points="8 6 2 12 8 18"></polyline>
            </svg>
            <span>Explore Code</span>
          </Link>
        </div>
      </header>

      {/* Index Status Banner if not ready */}
      {!loadingStatus && indexStatus && indexStatus.status !== 'ready' && (
        <div className="alert-card glass-card warning" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
              Code Search Notice
            </div>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary, #94a3b8)' }}>
              {indexStatus.status === 'not_built'
                ? 'Please enable code search for this project to get the most accurate answers.'
                : 'Your search index may need an update for the newest project files.'}
            </p>
          </div>
          <Link to={`/dashboard/projects/${projectId}/search`} className="btn btn-secondary btn-sm">
            Enable Code Search
          </Link>
        </div>
      )}

      {/* Main RAG Query Card */}
      <div className="glass-card" style={{ padding: '1.75rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <label htmlFor="rag-question-input" style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-primary, #f8fafc)' }}>
            Ask a Question about this Project
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary, #94a3b8)' }}>
            <label htmlFor="rag-topk-select">Context Sources:</label>
            <select
              id="rag-topk-select"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              disabled={asking}
              className="select-input"
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                color: '#fff',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '6px',
                padding: '0.25rem 0.5rem',
                fontSize: '0.85rem',
              }}
            >
              {[1, 2, 3, 5, 7, 10].map((k) => (
                <option key={k} value={k} style={{ background: '#1e293b', color: '#fff' }}>
                  {k} sources
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ position: 'relative', marginBottom: '1rem' }}>
          <textarea
            id="rag-question-input"
            rows="3"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={asking}
            placeholder="e.g., Where is JWT authentication implemented? (Press Enter to ask, Shift+Enter for new line)"
            style={{
              width: '100%',
              padding: '0.875rem 1rem',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              background: 'rgba(15, 23, 42, 0.6)',
              color: '#f8fafc',
              fontSize: '0.95rem',
              resize: 'vertical',
              boxSizing: 'border-box',
              outline: 'none',
              lineHeight: 1.5,
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          {/* Quick sample chips */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Quick Suggestions:
            </span>
            {sampleQueries.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                className="chip-btn"
                onClick={() => {
                  setQuestion(sample);
                  handleAsk(sample);
                }}
                disabled={asking}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '16px',
                  padding: '0.25rem 0.75rem',
                  fontSize: '0.75rem',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)';
                  e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.4)';
                  e.currentTarget.style.color = '#fff';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                  e.currentTarget.style.color = '#cbd5e1';
                }}
              >
                {sample}
              </button>
            ))}
          </div>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => handleAsk()}
            disabled={asking || !question.trim()}
            id="ask-codesage-btn"
            style={{ minWidth: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
          >
            {asking ? (
              <>
                <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="16"></circle>
                </svg>
                <span>Analyzing Codebase...</span>
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                  <polyline points="2 17 12 22 22 17"></polyline>
                  <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
                <span>Ask AI</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Loading state indicator */}
      {asking && (
        <div className="glass-card" style={{ padding: '2.5rem', textAlign: 'center', marginBottom: '1.5rem' }}>
          <div className="loading-spinner" style={{ margin: '0 auto 1.25rem', width: '40px', height: '40px' }} />
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#f8fafc', fontWeight: 600 }}>
            CodeSage AI is analyzing your project...
          </h3>
          <p style={{ margin: 0, color: 'var(--text-secondary, #94a3b8)', fontSize: '0.9rem' }}>
            Finding relevant code &bull; Synthesizing answer
          </p>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="glass-card" style={{ padding: '1.25rem', marginBottom: '1.5rem', borderLeft: '4px solid #ef4444', background: 'rgba(239, 68, 68, 0.1)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" style={{ flexShrink: 0, marginTop: '2px' }}>
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <div>
              <div style={{ fontWeight: 600, color: '#fca5a5', marginBottom: '0.25rem' }}>AI Assistant Notice</div>
              <div style={{ fontSize: '0.9rem', color: '#fecaca' }}>{error}</div>
            </div>
          </div>
        </div>
      )}

      {/* RAG Answer Display */}
      {ragResult && (
        <div ref={answerRef} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '2rem' }}>
          {/* Answer Card */}
          <div className="glass-card" style={{ padding: '1.75rem', position: 'relative' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '1.25rem' }}>🤖</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc' }}>
                    AI Answer
                  </h3>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Grounded on {ragResult.sources?.length || 0} project sources
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleCopyAnswer}
                title="Copy answer to clipboard"
                style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
              >
                {copied ? '✓ Copied' : 'Copy Answer'}
              </button>
            </div>

            {/* Answer Text */}
            <div
              className="rag-answer-body"
              style={{
                fontSize: '1rem',
                lineHeight: 1.7,
                color: '#e2e8f0',
                whiteSpace: 'pre-wrap',
                fontFamily: 'inherit',
              }}
            >
              {ragResult.answer}
            </div>
          </div>

          {/* Sources Section (Phases 15, 16, 30, 31) */}
          <div className="glass-card" style={{ padding: '1.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc' }}>
                  Sources ({ragResult.sources?.length || 0})
                </h3>
              </div>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                Relevant code references
              </span>
            </div>

            {ragResult.sources && ragResult.sources.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                {ragResult.sources.map((source, index) => (
                  <div
                    key={source.chunk_id || index}
                    style={{
                      background: 'rgba(15, 23, 42, 0.5)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '8px',
                      padding: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.75rem',
                      transition: 'border-color 0.2s ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.4)')}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)')}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                      <span
                        style={{
                          background: 'rgba(99, 102, 241, 0.15)',
                          color: '#818cf8',
                          fontWeight: 700,
                          fontSize: '0.8rem',
                          borderRadius: '6px',
                          padding: '0.2rem 0.5rem',
                          minWidth: '24px',
                          textAlign: 'center',
                        }}
                      >
                        #{index + 1}
                      </span>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.95rem' }}>
                            {source.file_path}
                          </span>
                          <span
                            style={{
                              fontSize: '0.75rem',
                              color: '#94a3b8',
                              background: 'rgba(255, 255, 255, 0.06)',
                              padding: '0.15rem 0.4rem',
                              borderRadius: '4px',
                            }}
                          >
                            Lines {source.start_line}&ndash;{source.end_line}
                          </span>
                          {source.symbol_name && (
                            <span
                              style={{
                                fontSize: '0.75rem',
                                color: '#38bdf8',
                                background: 'rgba(56, 189, 248, 0.12)',
                                padding: '0.15rem 0.4rem',
                                borderRadius: '4px',
                              }}
                            >
                              {source.symbol_name}
                              {source.symbol_type ? ` (${source.symbol_type})` : ''}
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                          Language: {source.language || 'Code'}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <div
                        style={{
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          color: source.score >= 0.7 ? '#4ade80' : source.score >= 0.5 ? '#facc15' : '#94a3b8',
                          background: 'rgba(255, 255, 255, 0.05)',
                          padding: '0.25rem 0.6rem',
                          borderRadius: '6px',
                        }}
                      >
                        {(source.score * 100).toFixed(1)}% match
                      </div>

                      <Link
                        to={`/dashboard/projects/${projectId}/explorer?file=${encodeURIComponent(source.file_path)}`}
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
                        title="Open file in Explorer code viewer"
                      >
                        Open in Explorer &rarr;
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.9rem' }}>
                No external sources were retrieved for this response.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

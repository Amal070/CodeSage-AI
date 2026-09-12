import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';

export default function AiTest() {
  const { token, logout, BACKEND_URL } = useAuth();

  // Status state from GET /api/ai/health
  const [health, setHealth] = useState(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  // Prompt & Generation state
  const [prompt, setPrompt] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  // Quick sample queries for fast testing (Phase 25)
  const samplePrompts = [
    'What is FastAPI in one sentence?',
    'Explain this Python function:\ndef add(a, b):\n    return a + b',
    'What is JWT authentication?',
    'What is SQLAlchemy?',
    'Hello from CodeSage AI.',
  ];

  // 1. Fetch AI & Gemma Health from FastAPI (Phases 20 & 22)
  const fetchHealth = useCallback(async () => {
    if (!token) return;
    setLoadingHealth(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/ai/health`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      } else {
        setHealth({
          ollama: { available: false },
          model: { name: 'gemma:2b', available: false },
        });
      }
    } catch {
      setHealth({
        ollama: { available: false },
        model: { name: 'gemma:2b', available: false },
      });
    } finally {
      setLoadingHealth(false);
    }
  }, [BACKEND_URL, token, logout]);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  // 2. Send Prompt to Gemma via FastAPI (Phases 12, 13, 14, 21)
  const handleSendPrompt = async (e) => {
    if (e) e.preventDefault();
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) {
      setError('Prompt cannot be empty.');
      return;
    }

    setGenerating(true);
    setError(null);
    setResponse(null);
    setCopied(false);

    try {
      const payload = { prompt: cleanPrompt };
      if (showSystemPrompt && systemPrompt.trim()) {
        payload.system_prompt = systemPrompt.trim();
      }

      const res = await fetch(`${BACKEND_URL}/api/ai/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.status === 401) {
        logout();
        return;
      }

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate response from Gemma.');
      }

      setResponse(data);
    } catch (err) {
      setError(err.message || 'Error communicating with AI service.');
    } finally {
      setGenerating(false);
    }
  };

  const copyResponse = () => {
    if (!response?.response) return;
    navigator.clipboard.writeText(response.response);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isOllamaConnected = health?.ollama?.available;
  const isModelAvailable = health?.model?.available;

  return (
    <div className="ai-test-container animate-fade-in" id="ai-test-page">
      {/* Top Header Card */}
      <header className="analysis-header-card glass-card">
        <div className="analysis-header-left">
          <div className="crumb-tag font-mono" style={{ width: 'fit-content' }}>
            Day 13 &bull; Ollama + Gemma Connection
          </div>
          <h1 className="analysis-project-title" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px' }}>
            <span>AI Connection Test</span>
            <span className="badge badge-purple font-mono" style={{ fontSize: '11px', padding: '2px 8px' }}>
              Day 13
            </span>
          </h1>
          <p className="analysis-project-sub text-secondary font-mono" style={{ marginTop: '2px' }}>
            Local LLM inference via Ollama and Google Gemma, connected through FastAPI backend
          </p>
        </div>

        <div className="analysis-header-right">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={fetchHealth}
            disabled={loadingHealth}
            id="refresh-ai-health-btn"
            title="Refresh Ollama & Gemma status"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={loadingHealth ? 'animate-spin' : ''}
            >
              <path d="M23 4v6h-6"></path>
              <path d="M1 20v-6h6"></path>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            <span>Refresh Status</span>
          </button>
        </div>
      </header>

      {/* Model & Daemon Health Cards (Phase 22) */}
      <div className="ai-metrics-grid">
        {/* Card 1: Ollama Daemon Status */}
        <div className="card glass-card ai-metric-card" id="ollama-status-card">
          <div className="ai-metric-icon cyan">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
              <line x1="6" y1="6" x2="6.01" y2="6"></line>
              <line x1="6" y1="18" x2="6.01" y2="18"></line>
            </svg>
          </div>
          <div className="ai-metric-content">
            <span className="ai-metric-label font-mono">Ollama Daemon</span>
            <div className="ai-metric-value font-mono">
              {loadingHealth ? (
                <span className="text-secondary font-mono text-sm animate-pulse">Checking...</span>
              ) : isOllamaConnected ? (
                <span className="text-success font-bold" id="ollama-status-text">Connected</span>
              ) : (
                <span className="text-error font-bold" id="ollama-status-text">Unavailable</span>
              )}
            </div>
            <span className="ai-metric-sub font-mono">http://localhost:11434</span>
          </div>
        </div>

        {/* Card 2: Gemma Model Status */}
        <div className="card glass-card ai-metric-card" id="gemma-status-card">
          <div className="ai-metric-icon purple">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a10 10 0 1 0 10 10H12V2z"></path>
              <path d="M12 12L2.5 7.5"></path>
              <path d="M12 12v10"></path>
            </svg>
          </div>
          <div className="ai-metric-content">
            <span className="ai-metric-label font-mono">Configured Model</span>
            <div className="ai-metric-value font-mono">
              {loadingHealth ? (
                <span className="text-secondary font-mono text-sm animate-pulse">Checking...</span>
              ) : isModelAvailable ? (
                <span className="text-success font-bold" id="gemma-status-text">
                  {health?.model?.name || 'gemma:2b'} Available
                </span>
              ) : (
                <span className="text-warning font-bold" id="gemma-status-text">
                  {health?.model?.name || 'gemma:2b'} Not Installed
                </span>
              )}
            </div>
            <span className="ai-metric-sub font-mono">
              {isModelAvailable ? 'Ready for inference' : 'Pull via ollama'}
            </span>
          </div>
        </div>

        {/* Card 3: Integration Layer */}
        <div className="card glass-card ai-metric-card" id="flow-card">
          <div className="ai-metric-icon emerald">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
          </div>
          <div className="ai-metric-content">
            <span className="ai-metric-label font-mono">Integration Layer</span>
            <div className="ai-metric-value font-mono text-cyan" style={{ fontSize: '18px' }}>
              FastAPI &rarr; Ollama
            </div>
            <span className="ai-metric-sub font-mono">Protected with JWT</span>
          </div>
        </div>
      </div>

      {/* Main Prompt Testing Card (Phase 21) */}
      <section className="glass-card search-box-card" id="ai-prompt-section">
        <form onSubmit={handleSendPrompt} className="search-form" id="ai-test-form">
          <div style={{ width: '100%' }}>
            <label htmlFor="ai-prompt-input" className="font-mono text-xs text-secondary" style={{ display: 'block', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Prompt to Gemma:
            </label>
            <textarea
              id="ai-prompt-input"
              rows={4}
              className="ai-prompt-textarea font-mono"
              placeholder="Ask Gemma something... (e.g. What is FastAPI?)"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={generating}
            />
          </div>

          {/* Optional System Prompt Toggle (Phase 16) */}
          <div style={{ width: '100%' }}>
            <button
              type="button"
              className="btn btn-ghost btn-xs font-mono"
              onClick={() => setShowSystemPrompt(!showSystemPrompt)}
              id="toggle-system-prompt-btn"
              style={{ color: '#c084fc', paddingLeft: 0 }}
            >
              {showSystemPrompt ? '▲ Hide Optional System Prompt' : '▼ Add Optional System Prompt'}
            </button>

            {showSystemPrompt && (
              <div style={{ marginTop: '8px' }}>
                <input
                  type="text"
                  className="ai-system-input font-mono"
                  placeholder="System prompt (e.g., You are a concise software engineering assistant.)"
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  disabled={generating}
                  id="ai-system-prompt-input"
                />
              </div>
            )}
          </div>

          {/* Submit Action Row */}
          <div className="search-options-row" style={{ marginTop: '4px' }}>
            <span className="font-mono text-xs text-secondary">
              {prompt.length.toLocaleString()} / 10,000 characters
            </span>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={generating || !prompt.trim() || !isOllamaConnected}
              id="send-to-gemma-btn"
            >
              {generating ? (
                <>
                  <div className="loading-spinner-sm" style={{ width: '16px', height: '16px' }}></div>
                  <span>Gemma is thinking...</span>
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                  </svg>
                  <span>Send to Gemma</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Quick Sample Prompts (Phase 25) */}
        <div className="sample-queries-wrap" style={{ marginTop: '16px', paddingTop: '16px' }}>
          <span className="sample-label font-mono text-xs text-secondary">Try asking:</span>
          <div className="sample-chips">
            {samplePrompts.map((sp, idx) => (
              <button
                key={idx}
                type="button"
                className="sample-chip font-mono"
                onClick={() => setPrompt(sp)}
                disabled={generating}
              >
                &ldquo;{sp.length > 36 ? sp.slice(0, 36) + '...' : sp}&rdquo;
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Error State (Phase 24) */}
      {error && (
        <div className="indexing-error-banner glass-card animate-fade-in" id="ai-error-banner">
          <div className="alert-icon text-error">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <div>
            <h4 style={{ margin: 0, color: '#f87171' }}>Generation Error</h4>
            <p className="font-mono text-sm text-error" style={{ margin: '4px 0 0 0' }}>{error}</p>
          </div>
        </div>
      )}

      {/* Loading State (Phase 23) */}
      {generating && (
        <div className="glass-card search-loading-card animate-fade-in" id="ai-loading-state">
          <div className="loading-spinner-lg"></div>
          <h3 className="search-state-title">Gemma is thinking...</h3>
          <p className="text-secondary font-mono text-sm">
            Sending prompt via FastAPI to local Ollama &bull; Generating text response
          </p>
        </div>
      )}

      {/* Gemma Response Display (Phase 17) */}
      {response && (
        <section className="glass-card animate-fade-in" id="ai-response-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="badge badge-purple font-mono" id="response-model-badge">
                {response.model}
              </span>
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc' }}>Gemma Response</h3>
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-xs font-mono"
              onClick={copyResponse}
              id="copy-response-btn"
            >
              {copied ? '✓ Copied' : 'Copy Text'}
            </button>
          </div>

          <div className="ai-response-block font-mono" id="gemma-response-text">
            {response.response}
          </div>
        </section>
      )}
    </div>
  );
}

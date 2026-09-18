import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Icon } from './common/Icon';
import { useToast } from './common/Toast';

export default function ProjectChat() {
  const { projectId } = useParams();
  const { token, logout, BACKEND_URL } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  // State
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [topK, setTopK] = useState(5);
  const [sending, setSending] = useState(false);
  const [loadingStage, setLoadingStage] = useState('searching');
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [conversationId, setConversationId] = useState(null);

  // Project details & Index status
  const [projectName, setProjectName] = useState('');
  const [indexStatus, setIndexStatus] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Suggested Prompts
  const suggestedPrompts = [
    'Explain authentication.',
    'Where is JWT authentication implemented?',
    'Explain this function.',
    'Explain the database connection.',
    'How does the project upload process work?',
    'What does this file do?',
  ];

  // Contextual Follow-up Suggestions
  const followUpPrompts = [
    'Where is this implemented?',
    'Explain that function.',
    'Which function handles that?',
    'What happens after that?',
    'How does this connect to the database?',
  ];

  // Scroll chat to bottom
  const scrollToBottom = (behavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom('auto');
  }, [messages, sending]);

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
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/vector-index/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setIndexStatus(data);
      }
    } catch {
      // ignore
    }
  }, [BACKEND_URL, projectId, token]);

  // 3. Fetch Stored Chat History
  const fetchChatHistory = useCallback(async () => {
    if (!token || !projectId) return;
    setLoadingHistory(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/chat?limit=50`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      if (res.ok) {
        const historyData = await res.json();
        const formattedMessages = [];
        let latestConvId = null;
        historyData.forEach((item) => {
          if (item.conversation_id) {
            latestConvId = item.conversation_id;
          }
          // User message
          formattedMessages.push({
            id: `user-${item.id}`,
            role: 'user',
            content: item.message,
            timestamp: item.created_at,
            conversationId: item.conversation_id,
          });
          // Assistant response
          formattedMessages.push({
            id: `asst-${item.id}`,
            role: 'assistant',
            content: item.response,
            sources: [], // Historical summaries
            timestamp: item.created_at,
            conversationId: item.conversation_id,
          });
        });
        setMessages(formattedMessages);
        if (latestConvId) {
          setConversationId(latestConvId);
        }
      }
    } catch {
      // ignore
    } finally {
      setLoadingHistory(false);
    }
  }, [BACKEND_URL, projectId, token, logout, navigate]);

  useEffect(() => {
    fetchProject();
    fetchIndexStatus();
    fetchChatHistory();
  }, [fetchProject, fetchIndexStatus, fetchChatHistory]);

  // 4. Send Chat Message
  const handleSend = async (queryText = null) => {
    const textToSend = (queryText !== null ? queryText : input).trim();
    if (!textToSend || sending) return;

    setError(null);
    setInput('');

    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString(),
      conversationId: conversationId,
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setSending(true);
    setLoadingStage('searching');

    // Progressive stage transition for responsive UX
    const stageTimer = setTimeout(() => {
      setLoadingStage('generating');
    }, 2500);

    try {
      const res = await fetch(`${BACKEND_URL}/api/projects/${projectId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: textToSend,
          top_k: topK,
          conversation_id: conversationId,
        }),
      });

      if (res.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to receive AI chat response.');
      }

      // Update active conversation session ID
      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      const assistantMsg = {
        id: `asst-${data.chat_id || Date.now()}`,
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        timestamp: data.created_at || new Date().toISOString(),
        model: data.model || 'gemma:2b',
        conversationId: data.conversation_id,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err.message || 'An error occurred while communicating with CodeSage AI.');
    } finally {
      clearTimeout(stageTimer);
      setSending(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  // 5. New Chat (Start fresh conversation session)
  const handleNewChat = () => {
    setMessages([]);
    setConversationId(null);
    setError(null);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  // 6. Clear Chat History
  const handleClearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear conversation history for this project?')) {
      return;
    }

    try {
      const url = conversationId
        ? `${BACKEND_URL}/api/projects/${projectId}/chat?conversation_id=${conversationId}`
        : `${BACKEND_URL}/api/projects/${projectId}/chat`;

      const res = await fetch(url, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessages([]);
        setConversationId(null);
        setError(null);
      }
    } catch {
      setError('Failed to clear chat history.');
    }
  };

  // 6. Copy message to clipboard
  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    toast.success('Response copied to clipboard');
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Handle Enter key submit
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="dashboard-container" style={{ maxWidth: '1300px', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 40px)', minHeight: '650px' }}>
      {/* Navigation Header */}
      <header className="glass-nav" style={{ flexShrink: 0 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary, #94a3b8)' }}>
              Projects / {projectName || `Project #${projectId}`} /
            </span>
            <span style={{ fontSize: '0.85rem', color: '#a855f7', fontWeight: 600 }}>AI Assistant Chat</span>
            {conversationId && (
              <span
                style={{
                  fontSize: '0.7rem',
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  padding: '0.15rem 0.5rem',
                  borderRadius: '12px',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  fontWeight: 600,
                }}
              >
                Session #{conversationId}
              </span>
            )}
          </div>
          <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary, #f8fafc)' }}>
            AI Assistant Chat
          </h1>
          <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary, #94a3b8)' }}>
            Ask questions about your project and understand your code faster.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link
            to={`/dashboard/projects/${projectId}/analysis`}
            className="btn btn-secondary btn-sm"
            id="chat-nav-analysis"
          >
            Analysis
          </Link>
          <Link
            to={`/dashboard/projects/${projectId}/search`}
            className="btn btn-secondary btn-sm"
            id="chat-nav-search"
          >
            <span>Search Code</span>
          </Link>
          <Link
            to={`/dashboard/projects/${projectId}/ask`}
            className="btn btn-secondary btn-sm"
            id="chat-nav-ask"
          >
            AI Assistant
          </Link>
          <Link
            to={`/dashboard/projects/${projectId}/explorer`}
            className="btn btn-primary btn-sm"
            id="chat-nav-explorer"
          >
            Explore Code &rarr;
          </Link>
        </div>
      </header>

      {/* Index Status Warning if needed */}
      {indexStatus && indexStatus.status !== 'ready' && (
        <div
          className="glass-card"
          style={{
            flexShrink: 0,
            marginTop: '0.75rem',
            padding: '0.75rem 1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderLeft: '4px solid #f59e0b',
            background: 'rgba(245, 158, 11, 0.08)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.1rem' }}>⚠️</span>
            <span style={{ fontSize: '0.85rem', color: '#fbbf24' }}>
              Project search index is not ready. Please enable code search first for optimal answers.
            </span>
          </div>
          <Link to={`/dashboard/projects/${projectId}/search`} className="btn btn-secondary btn-sm" style={{ fontSize: '0.75rem' }}>
            Enable Search
          </Link>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div
          className="glass-card"
          style={{
            flexShrink: 0,
            marginTop: '0.75rem',
            padding: '0.75rem 1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderLeft: '4px solid #ef4444',
            background: 'rgba(239, 68, 68, 0.1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.1rem' }}>❌</span>
            <span style={{ fontSize: '0.85rem', color: '#fca5a5' }}>{error}</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ fontSize: '0.75rem' }}
            onClick={() => setError(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Chat Messages Container */}
      <div
        className="glass-card"
        style={{
          flex: 1,
          marginTop: '0.75rem',
          marginBottom: '0.75rem',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Chat Header Actions */}
        <div
          style={{
            padding: '0.6rem 1rem',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(15, 23, 42, 0.4)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#94a3b8' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span>
            <span>AI Assistant Active</span>
            <span>&bull;</span>
            <span>{conversationId ? `Session #${conversationId}` : 'New Session'}</span>
            <span>&bull;</span>
            <span>{messages.length} message{messages.length !== 1 ? 's' : ''}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <button
              type="button"
              onClick={handleNewChat}
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', borderColor: '#a855f7', color: '#d8b4fe' }}
              title="Start a fresh conversation session"
              id="new-chat-btn"
            >
              + New Chat
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: '#94a3b8' }}>
              <label htmlFor="chat-topk">Context:</label>
              <select
                id="chat-topk"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                disabled={sending}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: '#fff',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '4px',
                  padding: '0.15rem 0.4rem',
                  fontSize: '0.8rem',
                }}
              >
                {[3, 5, 7, 10].map((k) => (
                  <option key={k} value={k} style={{ background: '#0f172a' }}>
                    {k} sources
                  </option>
                ))}
              </select>
            </div>

            {messages.length > 0 && (
              <button
                type="button"
                onClick={handleClearHistory}
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
                title="Clear conversation history"
                id="clear-chat-history-btn"
              >
                Clear History
              </button>
            )}
          </div>
        </div>

        {/* Scrollable Messages Area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.25rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem',
          }}
        >
          {loadingHistory ? (
            <div style={{ textAlign: 'center', padding: '3rem 0', color: '#94a3b8' }}>
              <div className="loading-spinner" style={{ margin: '0 auto 1rem', width: '32px', height: '32px' }}></div>
              <p style={{ margin: 0, fontSize: '0.9rem' }}>Loading conversation history...</p>
            </div>
          ) : messages.length === 0 ? (
            /* Welcome Empty State */
            <div style={{ textAlign: 'center', margin: 'auto', maxWidth: '650px', padding: '2rem 1rem' }}>
              <div
                style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '16px',
                  background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(99, 102, 241, 0.2))',
                  border: '1px solid rgba(168, 85, 247, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--primary-500)',
                  margin: '0 auto 1.25rem',
                }}
              >
                <Icon name="ai" size={32} />
              </div>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.5rem' }}>
                Ask anything about this project
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.6, marginBottom: '1.5rem' }}>
                CodeSage AI searches your project code and provides accurate, grounded explanations of your architecture and logic.
              </p>

              <div style={{ textAlign: 'left', marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#a855f7', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
                  Suggested Questions
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.5rem' }}>
                  {suggestedPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => handleSend(prompt)}
                      className="btn btn-secondary btn-sm"
                      style={{
                        textAlign: 'left',
                        padding: '0.6rem 0.85rem',
                        fontSize: '0.85rem',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        justifyContent: 'flex-start',
                      }}
                    >
                      <span style={{ color: '#c084fc', marginRight: '0.5rem' }}>💬</span>
                      <span style={{ color: '#e2e8f0' }}>{prompt}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Active Messages List */
            messages.map((msg, idx) => (
              <div
                key={msg.id || idx}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  width: '100%',
                }}
              >
                {/* Message Header */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    marginBottom: '0.35rem',
                    fontSize: '0.75rem',
                    color: '#94a3b8',
                  }}
                >
                  <span style={{ fontWeight: 600, color: msg.role === 'user' ? '#818cf8' : '#c084fc' }}>
                    {msg.role === 'user' ? 'You' : 'CodeSage AI'}
                  </span>
                  {msg.timestamp && (
                    <span>&bull; {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  )}
                </div>

                {/* Message Bubble */}
                <div
                  style={{
                    maxWidth: msg.role === 'user' ? '75%' : '90%',
                    padding: msg.role === 'user' ? '0.75rem 1rem' : '1.25rem',
                    borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                    background:
                      msg.role === 'user'
                        ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(168, 85, 247, 0.25))'
                        : 'rgba(15, 23, 42, 0.65)',
                    border:
                      msg.role === 'user'
                        ? '1px solid rgba(99, 102, 241, 0.4)'
                        : '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
                  }}
                >
                  {/* Message Text */}
                  <div
                    style={{
                      fontSize: '0.95rem',
                      lineHeight: 1.65,
                      color: '#f1f5f9',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {msg.content}
                  </div>

                  {/* Assistant Actions & Source Citations */}
                  {msg.role === 'assistant' && (
                    <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                          {msg.sources && msg.sources.length > 0
                            ? `Sources (${msg.sources.length})`
                            : 'Grounded Analysis'}
                        </span>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}
                          onClick={() => handleCopy(msg.content, idx)}
                        >
                          {copiedIndex === idx ? '✓ Copied' : 'Copy'}
                        </button>
                      </div>

                      {/* Relevant Files Summary (Day 17) */}
                      {msg.sources && msg.sources.length > 0 && (() => {
                        const uniqueFiles = Array.from(new Set(msg.sources.map((s) => s.file_path))).filter(Boolean);
                        if (uniqueFiles.length === 0) return null;
                        return (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.65rem', alignItems: 'center' }}>
                            <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 600 }}>
                              Relevant files:
                            </span>
                            {uniqueFiles.map((fp) => (
                              <Link
                                key={fp}
                                to={`/dashboard/projects/${projectId}/explorer?file=${encodeURIComponent(fp)}`}
                                style={{
                                  fontSize: '0.72rem',
                                  fontFamily: 'monospace',
                                  color: '#a5b4fc',
                                  background: 'rgba(99, 102, 241, 0.12)',
                                  border: '1px solid rgba(99, 102, 241, 0.25)',
                                  padding: '0.15rem 0.45rem',
                                  borderRadius: '4px',
                                  textDecoration: 'none',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '0.25rem',
                                }}
                                title={`Open ${fp} in Code Explorer`}
                              >
                                <Icon name="file" size={12} />
                                <span>{fp}</span>
                              </Link>
                            ))}
                          </div>
                        );
                      })()}

                      {/* Source Badges */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                          {msg.sources.map((src, sIdx) => (
                            <div
                              key={src.chunk_id || sIdx}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                background: 'rgba(0, 0, 0, 0.3)',
                                border: '1px solid rgba(255, 255, 255, 0.06)',
                                borderRadius: '6px',
                                padding: '0.4rem 0.65rem',
                                fontSize: '0.8rem',
                                flexWrap: 'wrap',
                                gap: '0.5rem',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ color: '#818cf8', fontWeight: 600 }}>#{sIdx + 1}</span>
                                <span style={{ color: '#f8fafc', fontWeight: 500, fontFamily: 'monospace' }}>
                                  {src.file_path}
                                </span>
                                <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>
                                  (L{src.start_line}–{src.end_line})
                                </span>
                                {src.symbol_name && (
                                  <span style={{ color: '#38bdf8', fontSize: '0.75rem', background: 'rgba(56, 189, 248, 0.1)', padding: '0.1rem 0.3rem', borderRadius: '3px' }}>
                                    {src.symbol_name}
                                  </span>
                                )}
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span
                                  style={{
                                    fontSize: '0.75rem',
                                    color: src.score >= 0.7 ? '#4ade80' : '#facc15',
                                  }}
                                >
                                  {(src.score * 100).toFixed(0)}% match
                                </span>
                                <Link
                                  to={`/dashboard/projects/${projectId}/explorer?file=${encodeURIComponent(src.file_path)}`}
                                  className="btn btn-secondary btn-sm"
                                  style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem' }}
                                  title="View file in Explorer"
                                >
                                  Open &rarr;
                                </Link>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Follow-up Question Chips for latest assistant message */}
                  {msg.role === 'assistant' && idx === messages.length - 1 && !sending && (
                    <div style={{ marginTop: '0.85rem', paddingTop: '0.65rem', borderTop: '1px dashed rgba(255, 255, 255, 0.08)' }}>
                      <div style={{ fontSize: '0.72rem', color: '#a855f7', fontWeight: 600, marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Suggested Follow-ups
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                        {followUpPrompts.map((p) => (
                          <button
                            key={p}
                            type="button"
                            onClick={() => handleSend(p)}
                            className="btn btn-secondary btn-sm"
                            style={{
                              fontSize: '0.75rem',
                              padding: '0.2rem 0.55rem',
                              borderRadius: '12px',
                              background: 'rgba(168, 85, 247, 0.08)',
                              border: '1px solid rgba(168, 85, 247, 0.25)',
                              color: 'var(--text-primary)',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <Icon name="chat" size={12} />
                            <span>{p}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {/* Sending / Progressive Analyzing Bubble */}
          {sending && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%' }}>
              <div style={{ fontSize: '0.75rem', color: '#c084fc', marginBottom: '0.35rem', fontWeight: 600 }}>
                CodeSage AI
              </div>
              <div
                style={{
                  padding: '1rem 1.25rem',
                  borderRadius: '12px 12px 12px 2px',
                  background: 'rgba(15, 23, 42, 0.65)',
                  border: '1px solid rgba(168, 85, 247, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                }}
              >
                <div className="loading-spinner" style={{ width: '20px', height: '20px' }}></div>
                <div>
                  <div style={{ fontSize: '0.9rem', color: '#f8fafc', fontWeight: 500 }}>
                    {loadingStage === 'searching'
                      ? 'Finding relevant code in your project...'
                      : 'Generating AI response...'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {loadingStage === 'searching'
                      ? 'Analyzing project files and code context'
                      : 'Synthesizing answer with project code context'}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div
          style={{
            padding: '0.75rem 1rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            background: 'rgba(15, 23, 42, 0.5)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <textarea
              ref={inputRef}
              id="chat-input"
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
              placeholder="Ask about your project... (e.g. 'Explain authentication', 'Where is JWT implemented?')"
              style={{
                flex: 1,
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '8px',
                padding: '0.65rem 0.85rem',
                color: '#fff',
                fontSize: '0.95rem',
                resize: 'none',
                fontFamily: 'inherit',
                outline: 'none',
              }}
            />

            <button
              type="button"
              id="send-chat-btn"
              onClick={() => handleSend()}
              disabled={sending || !input.trim()}
              className="btn btn-primary"
              style={{
                padding: '0.65rem 1.25rem',
                height: '52px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                opacity: sending || !input.trim() ? 0.6 : 1,
              }}
            >
              {sending ? (
                <>
                  <div className="loading-spinner" style={{ width: '16px', height: '16px' }}></div>
                  <span>Thinking...</span>
                </>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                  </svg>
                  <span>Send</span>
                </>
              )}
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b' }}>
            <span>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for new line</span>
            <span>Only answers grounded in project source code are produced</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const resolveBackendUrl = () => {
  if (typeof window !== 'undefined' && window.__CODESAGE_BACKEND_URL__) {
    return window.__CODESAGE_BACKEND_URL__;
  }
  if (import.meta.env.VITE_BACKEND_URL) {
    return import.meta.env.VITE_BACKEND_URL;
  }
  if (typeof window !== 'undefined' && window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000';
  }
  return 'http://localhost:8000';
};

export const BACKEND_URL = resolveBackendUrl();

const AuthContext = createContext(null);

/**
 * Resilient fetch that automatically tries 127.0.0.1, localhost, and Vite dev server proxy
 * to prevent browser-level IPv6 loopback connection drops ("Failed to fetch").
 */
const resilientFetch = async (urlOrPath, options = {}) => {
  const isFullUrl = urlOrPath.startsWith('http://') || urlOrPath.startsWith('https://');
  const primaryUrl = isFullUrl ? urlOrPath : `${BACKEND_URL}${urlOrPath}`;

  try {
    return await fetch(primaryUrl, options);
  } catch (primaryErr) {
    const candidates = [];
    if (primaryUrl.includes('localhost:8000')) {
      candidates.push(primaryUrl.replace('localhost:8000', '127.0.0.1:8000'));
    } else if (primaryUrl.includes('127.0.0.1:8000')) {
      candidates.push(primaryUrl.replace('127.0.0.1:8000', 'localhost:8000'));
    }

    if (isFullUrl) {
      try {
        const parsed = new URL(urlOrPath);
        candidates.push(parsed.pathname + parsed.search);
      } catch {
        // ignore
      }
    } else {
      candidates.push(urlOrPath);
    }

    for (const altUrl of candidates) {
      try {
        const altRes = await fetch(altUrl, options);
        return altRes;
      } catch {
        // try next candidate
      }
    }
    throw primaryErr;
  }
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem('codesage_token') || null);
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('codesage_user');
    try {
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem('codesage_token');
    localStorage.removeItem('codesage_user');
    setToken(null);
    setUser(null);
  }, []);

  // Fetch current user from /api/auth/me whenever token is available or changes
  const fetchCurrentUser = useCallback(async (authToken) => {
    const activeToken = authToken || token;
    if (!activeToken) {
      setUser(null);
      setLoading(false);
      return null;
    }

    try {
      const res = await resilientFetch(`${BACKEND_URL}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${activeToken}`,
        },
      });

      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
        localStorage.setItem('codesage_user', JSON.stringify(userData));
        return userData;
      } else {
        // Token invalid or expired
        logout();
        return null;
      }
    } catch (err) {
      console.error('Failed to fetch current user:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [logout, token]);

  useEffect(() => {
    if (token) {
      fetchCurrentUser(token);
    } else {
      setLoading(false);
    }
  }, [token, fetchCurrentUser]);

  const login = async (email, password) => {
    const res = await resilientFetch(`${BACKEND_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || 'Login failed. Please verify your credentials.');
    }

    const receivedToken = data.access_token;
    localStorage.setItem('codesage_token', receivedToken);
    setToken(receivedToken);

    if (data.user) {
      setUser(data.user);
      localStorage.setItem('codesage_user', JSON.stringify(data.user));
    } else {
      await fetchCurrentUser(receivedToken);
    }

    return data;
  };

  const register = async (name, email, password) => {
    const res = await resilientFetch(`${BACKEND_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      let errorMsg = data.detail || 'Registration failed.';
      if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map((d) => d.msg || d.message).join(', ');
      }
      throw new Error(errorMsg);
    }

    return data;
  };

  const authFetch = async (endpoint, options = {}) => {
    const headers = {
      ...(options.headers || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await resilientFetch(`${BACKEND_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      logout();
    }

    return res;
  };

  const value = {
    token,
    user,
    loading,
    isAuthenticated: !!token,
    login,
    register,
    logout,
    fetchCurrentUser,
    authFetch,
    BACKEND_URL,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

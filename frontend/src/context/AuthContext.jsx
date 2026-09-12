import React, { createContext, useContext, useState, useEffect } from 'react';

export const BACKEND_URL = 'http://localhost:8000';

const AuthContext = createContext(null);

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

  // Fetch current user from /api/auth/me whenever token is available or changes
  const fetchCurrentUser = async (authToken) => {
    const activeToken = authToken || token;
    if (!activeToken) {
      setUser(null);
      setLoading(false);
      return null;
    }

    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
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
  };

  useEffect(() => {
    if (token) {
      fetchCurrentUser(token);
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = async (email, password) => {
    const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
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
    const res = await fetch(`${BACKEND_URL}/api/auth/register`, {
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

  const logout = () => {
    localStorage.removeItem('codesage_token');
    localStorage.removeItem('codesage_user');
    setToken(null);
    setUser(null);
  };

  const authFetch = async (endpoint, options = {}) => {
    const headers = {
      ...(options.headers || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${BACKEND_URL}${endpoint}`, {
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

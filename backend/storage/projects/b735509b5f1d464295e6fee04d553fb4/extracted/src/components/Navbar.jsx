import React from 'react';
import { useAuth } from '../hooks/useAuth';

export default function Navbar({ title }) {
  const { user, logout } = useAuth();
  return (
    <header className="navbar">
      <h2 className="navbar-brand">{title}</h2>
      {user && (
        <div className="user-info">
          <span>Welcome, {user.name}</span>
          <button onClick={logout}>Sign Out</button>
        </div>
      )}
    </header>
  );
}

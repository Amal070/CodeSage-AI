import { useState } from 'react';

export function useAuth() {
  const [user, setUser] = useState({ name: 'Jordan', email: 'jordan@taskflow.dev' });
  const logout = () => setUser(null);
  return { user, logout };
}

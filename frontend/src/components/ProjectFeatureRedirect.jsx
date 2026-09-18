import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProjectFeatureRedirect({ subpath = 'explorer' }) {
  const { token, BACKEND_URL } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function resolveProject() {
      const storedId = localStorage.getItem('codesage_active_project');
      if (storedId) {
        navigate(`/dashboard/projects/${storedId}/${subpath}`, { replace: true });
        return;
      }

      if (!token) {
        navigate('/login', { replace: true });
        return;
      }

      try {
        const res = await fetch(`${BACKEND_URL}/api/projects`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!active) return;

        if (res.ok) {
          const list = await res.json();
          if (Array.isArray(list) && list.length > 0) {
            const firstId = list[0].id;
            localStorage.setItem('codesage_active_project', String(firstId));
            navigate(`/dashboard/projects/${firstId}/${subpath}`, { replace: true });
            return;
          }
        }
      } catch {
        // ignore
      }

      // No projects found
      if (active) {
        navigate('/dashboard/projects', { replace: true });
      }
    }

    resolveProject().finally(() => {
      if (active) setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [BACKEND_URL, navigate, subpath, token]);

  if (loading) {
    return (
      <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', marginTop: '2rem' }}>
        <div className="loading-spinner" style={{ margin: '0 auto 1rem' }} />
        <p className="text-secondary font-mono">Opening {subpath}...</p>
      </div>
    );
  }

  return null;
}

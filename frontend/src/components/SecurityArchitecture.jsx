import React from 'react';

export default function SecurityArchitecture() {
  const tables = [
    {
      name: 'users',
      purpose: 'User accounts & authentication credentials',
      columns: ['id (PK)', 'name', 'email (UNIQUE, INDEX)', 'password_hash', 'created_at'],
      badge: 'Day 2 & Day 3 Active',
    },
    {
      name: 'projects',
      purpose: 'User code repositories and analyzed projects',
      columns: ['id (PK)', 'name', 'description', 'programming_language', 'framework', 'file_count', 'lines_of_code', 'user_id (FK)', 'created_at'],
      badge: 'Day 2 Schema',
    },
    {
      name: 'chat_history',
      purpose: 'Conversations with the AI code comprehension engine',
      columns: ['id (PK)', 'user_id (FK)', 'project_id (FK)', 'message', 'response', 'created_at'],
      badge: 'Day 2 Schema',
    },
    {
      name: 'uploaded_files',
      purpose: 'Parsed source files and vector embeddings metadata',
      columns: ['id (PK)', 'name', 'path', 'file_type', 'size', 'content', 'project_id (FK)', 'created_at'],
      badge: 'Day 2 Schema',
    },
  ];

  return (
    <div className="security-architecture-container animate-fade-in">
      {/* Top Banner */}
      <div className="architecture-grid">
        {/* Security Standards Card */}
        <div className="card glass-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon purple">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                </svg>
              </div>
              <div>
                <h3>Security &amp; Cryptography Protocols</h3>
                <p className="card-desc">Production-grade authentication safeguards</p>
              </div>
            </div>
            <span className="badge badge-success">Verified</span>
          </div>

          <div className="security-flow-list">
            <div className="flow-card">
              <div className="flow-num">01</div>
              <div className="flow-body">
                <h4>Salted Bcrypt Password Hashing</h4>
                <p>Passwords are never stored in plaintext. Each password receives a unique 128-bit salt and is hashed via bcrypt before writing to PostgreSQL.</p>
              </div>
            </div>

            <div className="flow-card">
              <div className="flow-num">02</div>
              <div className="flow-body">
                <h4>PyJWT Signed Access Tokens</h4>
                <p>Upon valid authentication, FastAPI generates a cryptographic JWT signed with an HMAC-SHA256 secret key and a 60-minute expiration window.</p>
              </div>
            </div>

            <div className="flow-card">
              <div className="flow-num">03</div>
              <div className="flow-body">
                <h4>Protected FastAPI Dependency Injection</h4>
                <p>The reusable <code>get_current_user</code> dependency parses the <code>Authorization: Bearer</code> header, validates expiration &amp; signature, and retrieves the User instance.</p>
              </div>
            </div>

            <div className="flow-card">
              <div className="flow-num">04</div>
              <div className="flow-body">
                <h4>No Sensitive Data Leakage</h4>
                <p>Pydantic response models guarantee password hashes and server secrets are strictly excluded from all API responses.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Database Tables Card */}
        <div className="card glass-card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon cyan">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
                </svg>
              </div>
              <div>
                <h3>PostgreSQL Schema Architecture</h3>
                <p className="card-desc">Database: <code>codesage_db</code> via Alembic Migrations</p>
              </div>
            </div>
            <span className="badge badge-info">5 Tables</span>
          </div>

          <div className="tables-grid">
            {tables.map((t) => (
              <div key={t.name} className="table-item-card">
                <div className="table-header">
                  <span className="table-name font-mono">{t.name}</span>
                  <span className="table-badge">{t.badge}</span>
                </div>
                <p className="table-purpose">{t.purpose}</p>
                <div className="table-cols">
                  {t.columns.map((c, i) => (
                    <span key={i} className="col-chip font-mono">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

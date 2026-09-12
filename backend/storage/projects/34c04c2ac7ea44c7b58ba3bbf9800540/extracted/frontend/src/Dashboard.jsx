import React from 'react';

export function DashboardView({ user, projects }) {
    return (
        <div className='dashboard-container'>
            <h1>Welcome to CodeSage AI Dashboard</h1>
            <p>User: {user.name}</p>
            <p>Active Projects: {projects.length}</p>
        </div>
    );
}

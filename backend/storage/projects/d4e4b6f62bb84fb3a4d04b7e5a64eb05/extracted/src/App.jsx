import React from 'react';
import Navbar from './components/Navbar';
import DashboardPage from './pages/DashboardPage';

export default function App() {
  return (
    <div className="app-container">
      <Navbar title="TaskFlow Manager" />
      <main className="main-content">
        <DashboardPage />
      </main>
    </div>
  );
}

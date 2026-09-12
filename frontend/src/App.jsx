import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import DashboardLayout from './components/DashboardLayout';
import DashboardOverview from './components/DashboardOverview';
import ProjectUpload from './components/ProjectUpload';
import ProjectAnalysis from './components/ProjectAnalysis';
import ProjectDependencies from './components/ProjectDependencies';
import ProjectExplorer from './components/ProjectExplorer';
import ProjectSearch from './components/ProjectSearch';
import ProjectRag from './components/ProjectRag';
import ProjectChat from './components/ProjectChat';
import AiTest from './components/AiTest';
import UserProfile from './components/UserProfile';
import SecurityArchitecture from './components/SecurityArchitecture';
import Login from './components/Login';
import Register from './components/Register';
import LandingPage from './components/LandingPage';
import './App.css';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Landing Page */}
          <Route path="/" element={<LandingPage />} />

          {/* Authentication Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected Dashboard Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardOverview />} />
            <Route path="projects" element={<ProjectUpload />} />
            <Route path="projects/upload" element={<ProjectUpload />} />
            <Route path="projects/:projectId" element={<ProjectAnalysis />} />
            <Route path="projects/:projectId/analysis" element={<ProjectAnalysis />} />
            <Route path="projects/:projectId/dependencies" element={<ProjectDependencies />} />
            <Route path="projects/:projectId/explorer" element={<ProjectExplorer />} />
            <Route path="projects/:projectId/search" element={<ProjectSearch />} />
            <Route path="projects/:projectId/ask" element={<ProjectRag />} />
            <Route path="projects/:projectId/rag" element={<ProjectRag />} />
            <Route path="projects/:projectId/chat" element={<ProjectChat />} />
            <Route path="profile" element={<UserProfile />} />
            <Route path="security" element={<SecurityArchitecture />} />
            <Route path="ai" element={<AiTest />} />
          </Route>

          {/* Convenience Aliases */}
          <Route path="/ai" element={<Navigate to="/dashboard/ai" replace />} />
          <Route path="/projects" element={<Navigate to="/dashboard/projects" replace />} />
          <Route path="/projects/upload" element={<Navigate to="/dashboard/projects" replace />} />
          <Route path="/profile" element={<Navigate to="/dashboard/profile" replace />} />

          {/* Catch-all Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

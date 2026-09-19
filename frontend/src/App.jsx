import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './components/common/Toast';
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
import ProjectFunctionDoc from './components/ProjectFunctionDoc';
import ApiDocumentation from './components/ApiDocumentation';
import AiTest from './components/AiTest';
import UserProfile from './components/UserProfile';
import SecurityArchitecture from './components/SecurityArchitecture';
import ProjectExport from './components/ProjectExport';
import Settings from './components/Settings';
import ProjectFeatureRedirect from './components/ProjectFeatureRedirect';
import Login from './components/Login';
import Register from './components/Register';
import LandingPage from './components/LandingPage';
import './App.css';

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
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
            <Route path="explorer" element={<ProjectFeatureRedirect subpath="explorer" />} />
            <Route path="analysis" element={<ProjectFeatureRedirect subpath="analysis" />} />
            <Route path="dependencies" element={<ProjectFeatureRedirect subpath="dependencies" />} />
            <Route path="docs" element={<ProjectFeatureRedirect subpath="docs" />} />
            <Route path="search" element={<ProjectFeatureRedirect subpath="search" />} />
            <Route path="chat" element={<ProjectFeatureRedirect subpath="chat" />} />
            <Route path="ask" element={<ProjectFeatureRedirect subpath="chat" />} />
            <Route path="projects/:projectId" element={<ProjectAnalysis />} />
            <Route path="projects/:projectId/analysis" element={<ProjectAnalysis />} />
            <Route path="projects/:projectId/dependencies" element={<ProjectDependencies />} />
            <Route path="projects/:projectId/explorer" element={<ProjectExplorer />} />
            <Route path="projects/:projectId/search" element={<ProjectSearch />} />
            <Route path="projects/:projectId/ask" element={<ProjectRag />} />
            <Route path="projects/:projectId/rag" element={<ProjectRag />} />
            <Route path="projects/:projectId/chat" element={<ProjectChat />} />
            <Route path="projects/:projectId/docs" element={<ProjectFunctionDoc />} />
            <Route path="projects/:projectId/functions" element={<ProjectFunctionDoc />} />
            <Route path="api-docs" element={<ApiDocumentation />} />
            <Route path="export" element={<ProjectExport />} />
            <Route path="settings" element={<Settings />} />
            <Route path="profile" element={<UserProfile />} />
            <Route path="security" element={<SecurityArchitecture />} />
            <Route path="ai" element={<AiTest />} />
          </Route>

          {/* Convenience Aliases */}
          <Route path="/ai" element={<Navigate to="/dashboard/ai" replace />} />
          <Route path="/chat" element={<Navigate to="/dashboard/chat" replace />} />
          <Route path="/search" element={<Navigate to="/dashboard/search" replace />} />
          <Route path="/explorer" element={<Navigate to="/dashboard/explorer" replace />} />
          <Route path="/analysis" element={<Navigate to="/dashboard/analysis" replace />} />
          <Route path="/docs" element={<Navigate to="/dashboard/docs" replace />} />
          <Route path="/dependencies" element={<Navigate to="/dashboard/dependencies" replace />} />
          <Route path="/api-docs" element={<Navigate to="/dashboard/api-docs" replace />} />
          <Route path="/projects" element={<Navigate to="/dashboard/projects" replace />} />
          <Route path="/projects/upload" element={<Navigate to="/dashboard/projects" replace />} />
          <Route path="/profile" element={<Navigate to="/dashboard/profile" replace />} />
          <Route path="/settings" element={<Navigate to="/dashboard/settings" replace />} />
          <Route path="/export" element={<Navigate to="/dashboard/export" replace />} />

          {/* Catch-all Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}

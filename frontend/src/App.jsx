import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import SiteLayout from "./components/SiteLayout.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import CandidateDashboardPage from "./pages/CandidateDashboardPage.jsx";
import CandidateSettingsPage from "./pages/CandidateSettingsPage.jsx";
import EmployerDashboardPage from "./pages/EmployerDashboardPage.jsx";
import EmployerPortalPage from "./features/employer/pages/EmployerPortalPage.jsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import JobDiscoveryPage from "./pages/JobDiscoveryPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import "./App.css";

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<SiteLayout />}>
          {/* Public Routes */}
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          {/* Public job discovery – accessible without login; login unlocks apply/accommodations */}
          <Route path="/jobs" element={<JobDiscoveryPage />} />

          {/* Candidate Protected Routes */}
          <Route element={<ProtectedRoute allowedRole="candidate" />}>
            <Route path="/candidate/dashboard" element={<CandidateDashboardPage />} />
            <Route path="/candidate/settings" element={<CandidateSettingsPage />} />
          </Route>

          {/* Employer Protected Routes */}
          <Route element={<ProtectedRoute allowedRole="employer" />}>
            <Route path="/employer/dashboard" element={<EmployerDashboardPage />} />
            <Route path="/employer/portal" element={<EmployerPortalPage />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

export default App;

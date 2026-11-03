import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

/**
 * ProtectedRoute Component
 * Guards routes requiring an authenticated session and optionally enforces
 * the authoritative backend user role (candidate vs employer).
 *
 * @param {Object} props
 * @param {"candidate" | "employer"} [props.allowedRole] Expected role required for route access
 * @param {React.ReactNode} [props.children] Optional nested child elements
 */
export function ProtectedRoute({ allowedRole, children }) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Show accessible screen-reader announcement while checking session
  if (isLoading) {
    return (
      <main id="main-content" className="auth-loading-main" tabIndex="-1">
        <div className="auth-loading-card" role="status" aria-live="polite">
          <p className="eyebrow">NEXABILITY AUTHENTICATION</p>
          <h2>Verifying session...</h2>
          <p className="loading-hint">Connecting to secure authentication service.</p>
        </div>
      </main>
    );
  }

  // Not authenticated: redirect to login preserving attempted destination
  if (!user || !isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // Role restriction enforcement: redirect to the user's correct dashboard (case-insensitive)
  const userRole = typeof user.role === "string" ? user.role.toLowerCase() : "";
  const targetRole = typeof allowedRole === "string" ? allowedRole.toLowerCase() : "";

  if (targetRole && userRole !== targetRole) {
    if (userRole === "candidate") {
      return <Navigate to="/candidate/dashboard" replace />;
    }
    if (userRole === "employer") {
      return <Navigate to="/employer/dashboard" replace />;
    }
    return <Navigate to="/" replace />;
  }

  return children ? children : <Outlet />;
}

export default ProtectedRoute;


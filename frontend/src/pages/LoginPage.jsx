import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

function LoginPage() {
  const { user, login, logout, isLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setStatus("");

    if (!email.trim() || !password) {
      setError("Please enter both email and password.");
      return;
    }

    try {
      const authenticatedUser = await login(email.trim(), password);
      setStatus("Successfully signed in.");

      // Check whether user was redirected from a protected route
      const destination = location.state?.from?.pathname;
      if (destination) {
        navigate(destination, { replace: true });
        return;
      }

      // Role-based navigation determined by authoritative backend response (case-insensitive)
      const userRole = (authenticatedUser?.role || "").toLowerCase();
      if (userRole === "candidate") {
        navigate("/candidate/dashboard", { replace: true });
      } else if (userRole === "employer") {
        navigate("/employer/dashboard", { replace: true });
      } else {
        navigate("/", { replace: true });
      }
    } catch (err) {
      const statusCode = err.status || null;
      if (err.isProxyError || statusCode === 502 || statusCode === 504) {
        setError(
          err.message ||
            "Proxy error: Unable to connect to backend server. Please verify proxy target is active."
        );
      } else if (err.isNetworkError || statusCode === 0) {
        setError(
          err.message ||
            "Network error: Unable to connect to server. Please check your internet connection."
        );
      } else if (statusCode === 404) {
        setError(err.message || "Not Found (404): Authentication service endpoint not found.");
      } else if (statusCode === 422) {
        setError(err.message || "Validation Error (422): Invalid credentials format.");
      } else if (statusCode === 429) {
        setError(
          err.message ||
            "Rate Limited (429): Too many sign-in attempts. Please wait a moment before trying again."
        );
      } else {
        setError(err.message || "Sign-in failed. Please check your credentials.");
      }
    }
  }

  const userRole = (user?.role || "").toLowerCase();
  const dashboardPath =
    userRole === "employer" ? "/employer/dashboard" : "/candidate/dashboard";

  return (
    <main id="main-content" className="auth-main" tabIndex="-1">
      <section className="auth-panel" aria-labelledby="login-title">
        <p className="eyebrow">Sign in</p>
        <h1 id="login-title">Welcome back to your next opportunity.</h1>
        <p>Use your NexAbility account to continue.</p>

        {user ? (
          <div className="auth-authenticated" role="status">
            <p className="form-status">
              Signed in as <strong>{user.email || user.full_name || "Authenticated User"}</strong>
              {user.role ? ` (${user.role.toUpperCase()})` : ""}
            </p>
            <div className="auth-actions">
              <Link className="btn btn-primary" to={dashboardPath}>
                Go to Dashboard
              </Link>
              <button
                className="btn btn-secondary"
                type="button"
                onClick={logout}
                disabled={isLoading}
              >
                Sign Out
              </button>
            </div>
          </div>
        ) : (
          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div>
              <label className="field-label" htmlFor="login-email">
                Email address
              </label>
              <input
                className="field-control"
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="field-label" htmlFor="login-password">
                Password
              </label>
              <input
                className="field-control"
                id="login-password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <button className="btn btn-primary" type="submit" disabled={isLoading}>
              {isLoading ? "Signing In..." : "Sign In"}
            </button>
          </form>
        )}

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}

        {status && !user ? (
          <p className="form-status" role="status">
            {status}
          </p>
        ) : null}

        {!user && (
          <p>
            New to NexAbility? <Link to="/register">Create an account</Link>
          </p>
        )}
      </section>
    </main>
  );
}

export default LoginPage;

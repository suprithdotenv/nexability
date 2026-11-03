import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

function LoginPage() {
  const { user, login, loginWithGoogle, logout, isLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const googleBtnRef = useRef(null);

  const handlePostLoginRedirect = useCallback(
    (authenticatedUser) => {
      const destination = location.state?.from?.pathname;
      if (destination) {
        navigate(destination, { replace: true });
        return;
      }
      const userRole = (authenticatedUser?.role || "").toLowerCase();
      if (userRole === "candidate") {
        navigate("/candidate/dashboard", { replace: true });
      } else if (userRole === "employer") {
        navigate("/employer/dashboard", { replace: true });
      } else {
        navigate("/", { replace: true });
      }
    },
    [location.state, navigate]
  );

  const handleGoogleCredentialResponse = useCallback(
    async (response) => {
      if (!response?.credential) {
        setError("Google authentication was cancelled or returned no credentials.");
        return;
      }
      setError("");
      setStatus("");
      try {
        const authenticatedUser = await loginWithGoogle(response.credential);
        setStatus("Successfully signed in with Google.");
        handlePostLoginRedirect(authenticatedUser);
      } catch (err) {
        setError(err.message || "Google sign-in failed. Please try again.");
      }
    },
    [loginWithGoogle, handlePostLoginRedirect]
  );

  // Initialize Google Identity Services with standard account-selection behavior
  useEffect(() => {
    const googleClientId =
      import.meta.env.VITE_GOOGLE_CLIENT_ID ||
      "163519778778-rdkrj9o2hihjese3j0856ec87uaolpod.apps.googleusercontent.com";

    function initGoogle(clientId) {
      try {
        if (!window.google?.accounts?.id) return;

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: handleGoogleCredentialResponse,
          auto_select: false, // Ensures user chooses their account rather than auto-selecting
          cancel_on_tap_outside: true,
          context: "signin",
        });

        if (googleBtnRef.current) {
          googleBtnRef.current.innerHTML = "";
          window.google.accounts.id.renderButton(googleBtnRef.current, {
            type: "standard",
            theme: "outline",
            size: "large",
            width: 320,
            text: "signin_with",
            shape: "rectangular",
            logo_alignment: "left",
          });
        }
      } catch {
        // Fallback gracefully if blocked by browser privacy settings
      }
    }

    if (!window.google?.accounts?.id && !document.getElementById("google-gsi-client")) {
      const script = document.createElement("script");
      script.id = "google-gsi-client";
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = () => initGoogle(googleClientId);
      document.body.appendChild(script);
    } else if (window.google?.accounts?.id) {
      initGoogle(googleClientId);
    }

    return () => {
      try {
        window.google?.accounts?.id?.cancel();
      } catch {
        // Ignore cleanup errors
      }
    };
  }, [handleGoogleCredentialResponse]);

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
      handlePostLoginRedirect(authenticatedUser);
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
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label className="field-label" htmlFor="login-password">
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  style={{ fontSize: "0.875rem", color: "var(--color-primary, #0c66e4)", textDecoration: "none" }}
                >
                  Forgot password?
                </Link>
              </div>
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

            <button className="btn btn-primary" type="submit" disabled={isLoading} style={{ width: "100%" }}>
              {isLoading ? "Signing In..." : "Sign In"}
            </button>

            <div style={{ display: "flex", alignItems: "center", margin: "1.25rem 0", color: "#6b778c" }}>
              <hr style={{ flex: 1, border: "none", borderTop: "1px solid #dfe1e6" }} />
              <span style={{ padding: "0 0.75rem", fontSize: "0.875rem" }}>or</span>
              <hr style={{ flex: 1, border: "none", borderTop: "1px solid #dfe1e6" }} />
            </div>

            <div
              ref={googleBtnRef}
              style={{ display: "flex", justifyContent: "center", minHeight: "44px" }}
              aria-label="Google Sign-In Option"
            />
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

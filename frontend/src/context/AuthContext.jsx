import { useEffect, useState } from "react";
import { authService, tokenStore } from "../api/index.js";
import { AuthContext } from "./authContextInstance.js";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Check login status and initialize authenticated session on mount
  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      setIsLoading(true);
      setAuthError(null);

      try {
        // 1. Check whether an existing in-memory access token is available and valid
        if (tokenStore.getAccessToken()) {
          const userProfile = await authService.getCurrentUser();
          if (isMounted) {
            setUser(userProfile);
          }
          return;
        }

        // 2. If in-memory refresh token is available, attempt session refresh
        if (tokenStore.getRefreshToken()) {
          await authService.refreshSession();
          const userProfile = await authService.getCurrentUser();
          if (isMounted) {
            setUser(userProfile);
          }
          return;
        }

        // 3. Attempt session refresh using the backend's confirmed refresh-cookie mechanism, when applicable
        try {
          await authService.refreshSession();
          const userProfile = await authService.getCurrentUser();
          if (isMounted) {
            setUser(userProfile);
          }
          return;
        } catch {
          // No active session or cookie available; proceed as unauthenticated guest
        }

        if (isMounted) {
          setUser(null);
        }
      } catch {
        tokenStore.clearTokens();
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    initAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  /**
   * Authenticate user with email and password
   * Issues tokens, loads authoritative profile, and updates application state.
   */
  async function login(email, password) {
    setIsLoading(true);
    setAuthError(null);
    try {
      const { user: userProfile } = await authService.login(email, password);
      setUser(userProfile);
      return userProfile;
    } catch (err) {
      setUser(null);
      setAuthError(err.message || "Failed to sign in");
      throw err;
    } finally {
      setIsLoading(false);
    }
  }

  /**
   * Authenticate user with Google OAuth ID token
   */
  async function loginWithGoogle(credential) {
    setIsLoading(true);
    setAuthError(null);
    try {
      const { user: userProfile } = await authService.loginWithGoogle(credential);
      setUser(userProfile);
      return userProfile;
    } catch (err) {
      setUser(null);
      setAuthError(err.message || "Google sign-in failed");
      throw err;
    } finally {
      setIsLoading(false);
    }
  }

  /**
   * Terminate user session
   * Calls logout endpoint, wipes in-memory credentials, and clears application state.
   */
  async function logout() {
    setIsLoading(true);
    setAuthError(null);
    try {
      await authService.logout();
    } catch {
      // Always complete state clearance regardless of network/server logout errors
    } finally {
      tokenStore.clearTokens();
      setUser(null);
      setIsLoading(false);
    }
  }

  const value = {
    user,
    isAuthenticated: Boolean(user && tokenStore.getAccessToken()),
    isLoading,
    authError,
    login,
    loginWithGoogle,
    logout,
    sendOtp: (email, purpose) => authService.sendOtp(email, purpose),
    verifyOtp: (email, purpose, otp) => authService.verifyOtp(email, purpose, otp),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;

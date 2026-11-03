/**
 * NexAbility Authentication API Service
 * Integrates strictly with confirmed live endpoints from OpenAPI schema.
 * Supports token storage, session refresh, role-based profile loading, and clean logout.
 */

import { apiClient, tokenStore } from "./client.js";

export const authService = {
  /**
   * Screen employer email domain for corporate eligibility
   * Endpoint: POST /api/v1/auth/employer/email/check
   * Body: { email: string }
   * Returns: { eligible: boolean, reason: string, domain: string | null }
   */
  async checkEmployerEmail(email) {
    return apiClient.post("/api/v1/auth/employer/email/check", { email });
  },

  /**
   * Send one-time passcode for registration or password reset
   * Endpoint: POST /api/v1/auth/otp/send
   * Body: { email: string, purpose: "CANDIDATE_REGISTRATION" | "EMPLOYER_REGISTRATION" | "PASSWORD_RESET" }
   * Returns: { message: string, expires_in: number | null }
   */
  async sendOtp(email, purpose) {
    return apiClient.post("/api/v1/auth/otp/send", { email, purpose });
  },

  /**
   * Verify one-time passcode to receive a temporary verification ticket
   * Note: The verification_ticket is a proof token for registration/reset, NOT an access token.
   * Endpoint: POST /api/v1/auth/otp/verify
   * Body: { email: string, purpose: "CANDIDATE_REGISTRATION" | "EMPLOYER_REGISTRATION" | "PASSWORD_RESET", otp: string }
   * Returns: { verified: boolean, message: string, verification_ticket: string, expires_in: number }
   */
  async verifyOtp(email, purpose, otp) {
    return apiClient.post("/api/v1/auth/otp/verify", { email, purpose, otp });
  },

  /**
   * Register a new candidate using the verified ticket
   * Endpoint: POST /api/v1/auth/candidate/register
   * Body: { full_name, email, password, phone, verification_ticket }
   * Returns: { id: string, email: string, full_name: string, role: string, message: string }
   */
  async registerCandidate({ full_name, email, password, phone = null, verification_ticket }) {
    return apiClient.post("/api/v1/auth/candidate/register", {
      full_name,
      email,
      password,
      phone: phone || null,
      verification_ticket,
    });
  },

  /**
   * Register a new employer using the verified ticket
   * Endpoint: POST /api/v1/auth/employer/register
   * Body: { full_name, company_name, email, password, phone, website, verification_ticket }
   * Returns: { id, email, full_name, company_name, role, verification_status, message }
   */
  async registerEmployer({
    full_name,
    company_name,
    email,
    password,
    phone = null,
    website = null,
    verification_ticket,
  }) {
    return apiClient.post("/api/v1/auth/employer/register", {
      full_name,
      company_name,
      email,
      password,
      phone: phone || null,
      website: website || null,
      verification_ticket,
    });
  },

  /**
   * Sign in with email and password
   * Endpoint: POST /api/v1/auth/login
   * Body: { email: string, password: string }
   * Returns: { access_token: string, refresh_token: string, token_type: string, expires_in: number }
   */
  async login(email, password) {
    const data = await apiClient.post("/api/v1/auth/login", { email, password });
    if (data?.access_token) {
      tokenStore.setAccessToken(data.access_token);
    }
    if (data?.refresh_token) {
      // In-memory only, never persisted to localStorage
      tokenStore.setRefreshToken(data.refresh_token);
    }

    // Retrieve enriched user profile with backend authoritative role
    const user = await this.getCurrentUser();
    return { tokens: data, user };
  },

  /**
   * Refresh session using refresh token or session cookie
   * Endpoint: POST /api/v1/auth/refresh
   * Body: { refresh_token: string }
   * Returns: { access_token: string, refresh_token: string, token_type: string, expires_in: number }
   */
  async refreshSession() {
    const refreshToken = tokenStore.getRefreshToken();
    if (!refreshToken) {
      throw new Error("No refresh token available in current session.");
    }

    const data = await apiClient.post("/api/v1/auth/refresh", { refresh_token: refreshToken });
    if (data?.access_token) {
      tokenStore.setAccessToken(data.access_token);
    }
    if (data?.refresh_token) {
      tokenStore.setRefreshToken(data.refresh_token);
    }
    return data;
  },

  /**
   * Logout current session
   * Endpoint: POST /api/v1/auth/logout
   * Body: { refresh_token: string }
   * Returns: { message: string }
   */
  async logout() {
    const refreshToken = tokenStore.getRefreshToken() || "";
    try {
      if (refreshToken) {
        await apiClient.post("/api/v1/auth/logout", { refresh_token: refreshToken });
      }
    } finally {
      tokenStore.clearTokens();
    }
  },

  /**
   * Get current authenticated user account and enrich with role profile
   * Endpoint: GET /api/v1/auth/me
   * Requires: Bearer access token
   */
  async getCurrentUser() {
    const account = await apiClient.get("/api/v1/auth/me", { requiresAuth: true });
    if (!account) {
      throw new Error("Unable to retrieve user account.");
    }

    // Normalize authoritative backend role to lowercase ("candidate" | "employer" | "admin")
    const rawRole = typeof account.role === "string" ? account.role : "";
    const normalizedRole = rawRole.toLowerCase();

    let enrichedUser = {
      id: account.id,
      email: account.email,
      role: normalizedRole, // Normalized to lowercase for robust client-side role matching
      rawRole,              // Preserved original backend enum ("CANDIDATE" | "EMPLOYER")
      is_active: account.is_active,
      full_name: "",
      company_name: "",
      email_domain: "",
      website: null,
      phone: null,
      verification_status: null,
    };

    // Enrich based on role
    if (normalizedRole === "candidate") {
      try {
        const candidateProfile = await this.getCandidateProfile();
        if (candidateProfile) {
          enrichedUser = {
            ...enrichedUser,
            full_name: candidateProfile.full_name || "",
            phone: candidateProfile.phone || null,
          };
        }
      } catch {
        // Fall back to base account if candidate profile is pending
      }
    } else if (normalizedRole === "employer") {
      try {
        const employerProfile = await this.getEmployerProfile();
        if (employerProfile) {
          enrichedUser = {
            ...enrichedUser,
            full_name: employerProfile.full_name || "",
            company_name: employerProfile.company_name || "",
            email_domain: employerProfile.email_domain || "",
            website: employerProfile.website || null,
            phone: employerProfile.phone || null,
            verification_status: employerProfile.verification_status || "PENDING",
          };
        }
      } catch {
        enrichedUser.verification_status = "PENDING";
      }
    }

    return enrichedUser;
  },

  /**
   * Retrieve candidate profile
   * Endpoint: GET /api/v1/candidates/me
   */
  async getCandidateProfile() {
    return apiClient.get("/api/v1/candidates/me", { requiresAuth: true });
  },

  /**
   * Retrieve employer profile
   * Endpoint: GET /api/v1/employers/me
   */
  async getEmployerProfile() {
    return apiClient.get("/api/v1/employers/me", { requiresAuth: true });
  },

  /**
   * Request password reset OTP
   * Endpoint: POST /api/v1/auth/password/forgot
   */
  async forgotPassword(email) {
    return apiClient.post("/api/v1/auth/password/forgot", { email });
  },

  /**
   * Reset password with verification ticket
   * Endpoint: POST /api/v1/auth/password/reset
   */
  async resetPassword({ email, verification_ticket, new_password }) {
    return apiClient.post("/api/v1/auth/password/reset", {
      email,
      verification_ticket,
      new_password,
    });
  },

  /**
   * Google Authentication
   * Endpoint: POST /api/v1/auth/google
   * Body: { credential: string }
   */
  async loginWithGoogle(credential) {
    if (!credential) {
      throw new Error("Google credential is required for sign-in.");
    }
    const data = await apiClient.post("/api/v1/auth/google", { credential });
    if (data?.access_token) {
      tokenStore.setAccessToken(data.access_token);
    }
    if (data?.refresh_token) {
      tokenStore.setRefreshToken(data.refresh_token);
    }
    const user = await this.getCurrentUser();
    return { tokens: data, user };
  },

  /**
   * Google Authentication Status
   * Note: The live backend OpenAPI schema defines `/api/v1/auth/google`.
   */
  isGoogleAuthAvailable: true,
};

// Register refresh handler with client token store
tokenStore.registerRefreshHandler(() => authService.refreshSession());

export default authService;

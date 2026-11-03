/**
 * NexAbility Candidate API Service
 * Integrates directly with live FastAPI endpoints:
 * - Profile: GET /api/v1/candidates/me, PATCH /api/v1/candidates/me
 * - Resume: POST /api/v1/candidates/me/resume, GET /api/v1/candidates/me/resume,
 *           GET /api/v1/candidates/me/resume/download, DELETE /api/v1/candidates/me/resume
 * - Accessibility: GET /api/v1/candidates/me/accessibility, POST /api/v1/candidates/me/accessibility,
 *                  PATCH /api/v1/candidates/me/accessibility/{id}, DELETE /api/v1/candidates/me/accessibility/{id}
 * - Voluntary declaration stubs guarded for Phase 2.1
 */

import { apiClient } from "./client.js";

export const candidateService = {
  /**
   * Deployment status of the voluntary disability self-declaration endpoint.
   * Enabled: /api/v1/candidates/me/declaration is mounted and supported by backend router.
   */
  isDeclarationSupported: true,

  // -------------------------------------------------------------
  // Candidate Profile Endpoints
  // -------------------------------------------------------------

  /**
   * Retrieve current candidate profile
   * Endpoint: GET /api/v1/candidates/me
   * Returns: { id, user_id, email, full_name, phone, created_at, updated_at }
   */
  async getProfile() {
    return apiClient.get("/api/v1/candidates/me", { requiresAuth: true });
  },

  /**
   * Update candidate profile
   * Endpoint: PATCH /api/v1/candidates/me
   * Body: { full_name?: string (2-150), phone?: string (max 20) }
   * Returns: CandidateProfileResponse
   */
  async updateProfile({ full_name, phone } = {}) {
    const payload = {};
    if (full_name !== undefined) {
      payload.full_name = full_name.trim();
    }
    if (phone !== undefined) {
      payload.phone = phone ? phone.trim() : null;
    }
    return apiClient.patch("/api/v1/candidates/me", payload, { requiresAuth: true });
  },

  // -------------------------------------------------------------
  // Resume Management Endpoints
  // -------------------------------------------------------------

  /**
   * Retrieve candidate's active resume metadata
   * Endpoint: GET /api/v1/candidates/me/resume
   * Returns: ResumeMetadataResponse or null if no active resume
   */
  async getResume() {
    try {
      return await apiClient.get("/api/v1/candidates/me/resume", { requiresAuth: true });
    } catch (err) {
      if (err.status === 404) {
        return null;
      }
      throw err;
    }
  },

  /**
   * Upload or replace candidate resume (PDF or DOCX, max 5MB)
   * Endpoint: POST /api/v1/candidates/me/resume
   * Body: FormData with "file"
   * Returns: ResumeMetadataResponse
   */
  async uploadResume(file) {
    if (!file) {
      throw new Error("Please select a resume file to upload.");
    }

    const validExtensions = [".pdf", ".docx"];
    const fileName = file.name.toLowerCase();
    const hasValidExt = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!hasValidExt) {
      throw new Error("Unsupported file format. Only PDF and DOCX files are accepted.");
    }

    const maxBytes = 5 * 1024 * 1024; // 5MB limit matching backend settings.MAX_UPLOAD_SIZE_BYTES
    if (file.size > maxBytes) {
      throw new Error("File size exceeds maximum allowed limit of 5MB.");
    }

    const formData = new FormData();
    formData.append("file", file);

    return apiClient.post("/api/v1/candidates/me/resume", formData, {
      requiresAuth: true,
    });
  },

  /**
   * Download candidate's active resume binary stream
   * Endpoint: GET /api/v1/candidates/me/resume/download
   * Returns: { blob: Blob, filename: string, mimeType: string }
   */
  async downloadResume() {
    return apiClient.download("/api/v1/candidates/me/resume/download", {
      requiresAuth: true,
    });
  },

  /**
   * Delete candidate's active resume
   * Endpoint: DELETE /api/v1/candidates/me/resume
   * Returns: { message: string }
   */
  async deleteResume() {
    return apiClient.delete("/api/v1/candidates/me/resume", { requiresAuth: true });
  },

  // -------------------------------------------------------------
  // Candidate Accessibility Preferences Endpoints
  // -------------------------------------------------------------

  /**
   * List candidate's accessibility preferences
   * Endpoint: GET /api/v1/candidates/me/accessibility
   * Returns: list[AccessibilityPreferenceResponse]
   */
  async getAccessibilityPreferences() {
    return apiClient.get("/api/v1/candidates/me/accessibility", { requiresAuth: true });
  },

  /**
   * Add a new accessibility preference
   * Endpoint: POST /api/v1/candidates/me/accessibility
   * Body: { category: string (2-50), preference: string (2-150), details?: string (max 500), is_active?: bool }
   * Returns: AccessibilityPreferenceResponse
   */
  async createAccessibilityPreference({
    category,
    preference,
    details = null,
    is_active = true,
  }) {
    if (!category || category.trim().length < 2) {
      throw new Error("Accommodation category is required (min 2 characters).");
    }
    if (!preference || preference.trim().length < 2) {
      throw new Error("Preference description is required (min 2 characters).");
    }

    const payload = {
      category: category.trim(),
      preference: preference.trim(),
      details: details && details.trim() ? details.trim() : null,
      is_active: Boolean(is_active),
    };

    return apiClient.post("/api/v1/candidates/me/accessibility", payload, {
      requiresAuth: true,
    });
  },

  /**
   * Update an existing accessibility preference
   * Endpoint: PATCH /api/v1/candidates/me/accessibility/{preference_id}
   * Body: { category?: str, preference?: str, details?: str, is_active?: bool }
   * Returns: AccessibilityPreferenceResponse
   */
  async updateAccessibilityPreference(preferenceId, {
    category,
    preference,
    details,
    is_active,
  } = {}) {
    if (!preferenceId) {
      throw new Error("Preference ID is required for update.");
    }

    const payload = {};
    if (category !== undefined) payload.category = category.trim();
    if (preference !== undefined) payload.preference = preference.trim();
    if (details !== undefined) payload.details = details && details.trim() ? details.trim() : null;
    if (is_active !== undefined) payload.is_active = Boolean(is_active);

    return apiClient.patch(
      `/api/v1/candidates/me/accessibility/${preferenceId}`,
      payload,
      { requiresAuth: true }
    );
  },

  /**
   * Delete an accessibility preference
   * Endpoint: DELETE /api/v1/candidates/me/accessibility/{preference_id}
   * Returns: { message: string }
   */
  async deleteAccessibilityPreference(preferenceId) {
    if (!preferenceId) {
      throw new Error("Preference ID is required for deletion.");
    }
    return apiClient.delete(`/api/v1/candidates/me/accessibility/${preferenceId}`, {
      requiresAuth: true,
    });
  },

  // -------------------------------------------------------------
  // Disability Declaration
  // -------------------------------------------------------------

  /**
   * Save voluntary disability declaration
   * Endpoint: PUT /api/v1/candidates/me/declaration
   */
  async saveDeclaration({ accepted = true, declaration_version = "v1" } = {}) {
    return apiClient.put(
      "/api/v1/candidates/me/declaration",
      { accepted, declaration_version },
      { requiresAuth: true }
    );
  },

  /**
   * Retrieve current disability declaration status
   * Endpoint: GET /api/v1/candidates/me/declaration
   */
  async getDeclaration() {
    try {
      return await apiClient.get("/api/v1/candidates/me/declaration", { requiresAuth: true });
    } catch (err) {
      if (err.status === 404) return null;
      throw err;
    }
  },

  /**
   * Withdraw voluntary disability declaration
   * Endpoint: DELETE /api/v1/candidates/me/declaration
   */
  async withdrawDeclaration() {
    return apiClient.delete("/api/v1/candidates/me/declaration", { requiresAuth: true });
  },

  // -------------------------------------------------------------
  // Public & Candidate Job Discovery & ML Matching
  // -------------------------------------------------------------

  /**
   * Retrieve ranked job matches for the authenticated candidate
   * Endpoint: GET /api/v1/candidates/me/matches
   * Query params: force_reprocess (bool), min_threshold (float)
   * Returns: CandidateMatchResponse
   */
  async getMatches({ forceReprocess = false, minThreshold = 60.0 } = {}) {
    const params = new URLSearchParams();
    if (forceReprocess) {
      params.append("force_reprocess", "true");
    }
    if (minThreshold !== undefined && minThreshold !== null) {
      params.append("min_threshold", String(minThreshold));
    }
    const query = params.toString() ? `?${params.toString()}` : "";
    return apiClient.get(`/api/v1/candidates/me/matches${query}`, {
      requiresAuth: true,
    });
  },

  /**
   * List available jobs publicly or with candidate profile context
   * Endpoint: GET /api/v1/jobs
   */
  async getJobs() {
    return apiClient.get("/api/v1/jobs");
  },

  /**
   * Retrieve detailed public job listing
   * Endpoint: GET /api/v1/jobs/{job_id}
   */
  async getJob(jobId) {
    if (!jobId) throw new Error("Job ID is required.");
    return apiClient.get(`/api/v1/jobs/${jobId}`);
  },

  // -------------------------------------------------------------
  // Candidate Job Applications
  // -------------------------------------------------------------

  /**
   * Apply for a specific job listing
   * Endpoint: POST /api/v1/candidates/me/jobs/{job_id}/apply
   */
  async applyForJob(jobId, { cover_note = null } = {}) {
    if (!jobId) throw new Error("Job ID is required to submit application.");
    return apiClient.post(
      `/api/v1/candidates/me/jobs/${jobId}/apply`,
      { cover_note: cover_note && cover_note.trim() ? cover_note.trim() : null },
      { requiresAuth: true }
    );
  },

  /**
   * List candidate's submitted job applications
   * Endpoint: GET /api/v1/candidates/me/applications
   */
  async getMyApplications() {
    return apiClient.get("/api/v1/candidates/me/applications", { requiresAuth: true });
  },

  // -------------------------------------------------------------
  // Candidate Accommodation Requests
  // -------------------------------------------------------------

  /**
   * Request workplace / interview accommodation for a job
   * Endpoint: POST /api/v1/candidates/me/jobs/{job_id}/accommodations
   */
  async requestAccommodation(jobId, { facility, description = null } = {}) {
    if (!jobId) throw new Error("Job ID is required to request accommodation.");
    if (!facility || !facility.trim()) {
      throw new Error("Facility or accommodation name is required.");
    }
    return apiClient.post(
      `/api/v1/candidates/me/jobs/${jobId}/accommodations`,
      {
        facility: facility.trim(),
        description: description && description.trim() ? description.trim() : null,
      },
      { requiresAuth: true }
    );
  },

  /**
   * List candidate's submitted accommodation requests
   * Endpoint: GET /api/v1/candidates/me/accommodations
   */
  async getMyAccommodations() {
    return apiClient.get("/api/v1/candidates/me/accommodations", { requiresAuth: true });
  },
};

export default candidateService;

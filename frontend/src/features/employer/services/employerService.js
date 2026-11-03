/**
 * NexAbility Employer API Service
 * Encapsulates all employer-related backend operations:
 * - Profile and verification
 * - Accessibility capabilities
 * - Job listings management
 * - Candidate applications
 * - Accommodation request inbox
 * - Dashboard analytics
 */

import { apiClient } from "../../../api/client.js";

export const employerService = {
  // -------------------------------------------------------------
  // Dashboard & Metrics
  // -------------------------------------------------------------
  async getDashboard() {
    return apiClient.get("/api/v1/employers/me/dashboard", { requiresAuth: true });
  },

  // -------------------------------------------------------------
  // Company Profile & Verification
  // -------------------------------------------------------------
  async getProfile() {
    return apiClient.get("/api/v1/employers/me", { requiresAuth: true });
  },

  async updateProfile(payload) {
    return apiClient.patch("/api/v1/employers/me", payload, { requiresAuth: true });
  },

  // -------------------------------------------------------------
  // Accessibility Capabilities
  // -------------------------------------------------------------
  async getAccessibilityCapabilities() {
    return apiClient.get("/api/v1/employers/me/accessibility", { requiresAuth: true });
  },

  async createAccessibilityCapability(payload) {
    return apiClient.post("/api/v1/employers/me/accessibility", payload, { requiresAuth: true });
  },

  async updateAccessibilityCapability(id, payload) {
    return apiClient.patch(`/api/v1/employers/me/accessibility/${id}`, payload, { requiresAuth: true });
  },

  async deleteAccessibilityCapability(id) {
    return apiClient.delete(`/api/v1/employers/me/accessibility/${id}`, { requiresAuth: true });
  },

  // -------------------------------------------------------------
  // Job Postings Management
  // -------------------------------------------------------------
  async getJobs() {
    return apiClient.get("/api/v1/employers/me/jobs", { requiresAuth: true });
  },

  async getJob(id) {
    return apiClient.get(`/api/v1/employers/me/jobs/${id}`, { requiresAuth: true });
  },

  async createJob(payload) {
    return apiClient.post("/api/v1/employers/me/jobs", payload, { requiresAuth: true });
  },

  async updateJob(id, payload) {
    return apiClient.patch(`/api/v1/employers/me/jobs/${id}`, payload, { requiresAuth: true });
  },

  async deleteJob(id) {
    return apiClient.delete(`/api/v1/employers/me/jobs/${id}`, { requiresAuth: true });
  },

  // -------------------------------------------------------------
  // Candidate Applications (Strictly Scoped)
  // -------------------------------------------------------------
  async getApplications(params = {}) {
    let url = "/api/v1/employers/me/applications";
    const searchParams = new URLSearchParams();
    if (params.status) searchParams.append("status", params.status);
    if (params.jobId) searchParams.append("job_id", params.jobId);
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
    return apiClient.get(url, { requiresAuth: true });
  },

  async getApplication(id) {
    return apiClient.get(`/api/v1/employers/me/applications/${id}`, { requiresAuth: true });
  },

  async updateApplicationStatus(id, status) {
    return apiClient.patch(
      `/api/v1/employers/me/applications/${id}/status`,
      { status },
      { requiresAuth: true }
    );
  },

  // -------------------------------------------------------------
  // Accommodation Request Inbox
  // -------------------------------------------------------------
  async getAccommodations(params = {}) {
    let url = "/api/v1/employers/me/accommodations";
    if (params.status) {
      url += `?status=${encodeURIComponent(params.status)}`;
    }
    return apiClient.get(url, { requiresAuth: true });
  },

  async getAccommodation(id) {
    return apiClient.get(`/api/v1/employers/me/accommodations/${id}`, { requiresAuth: true });
  },

  async respondToAccommodation(id, { status, response_message }) {
    return apiClient.patch(
      `/api/v1/employers/me/accommodations/${id}`,
      { status, response_message },
      { requiresAuth: true }
    );
  },

  // -------------------------------------------------------------
  // Job Description Documents
  // -------------------------------------------------------------
  async getJobDocuments() {
    return apiClient.get("/api/v1/employers/me/job-documents", { requiresAuth: true });
  },

  async deleteJobDocument(id) {
    return apiClient.delete(`/api/v1/employers/me/job-documents/${id}`, { requiresAuth: true });
  },
};

export default employerService;


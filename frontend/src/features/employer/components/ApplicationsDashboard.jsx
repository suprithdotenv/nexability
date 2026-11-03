import { useState, useEffect } from "react";
import employerService from "../services/employerService.js";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "APPLIED", label: "Applied (New)" },
  { value: "REVIEWING", label: "Under Review" },
  { value: "SHORTLISTED", label: "Shortlisted" },
  { value: "INTERVIEW", label: "Interview Scheduled" },
  { value: "ACCEPTED", label: "Offer Extended / Accepted" },
  { value: "REJECTED", label: "Archived / Not Selected" },
];

function ApplicationsDashboard({ selectedJobId }) {
  const [applications, setApplications] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [filterStatus, setFilterStatus] = useState("");
  const [filterJobId, setFilterJobId] = useState(selectedJobId || "");
  const [selectedApp, setSelectedApp] = useState(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  useEffect(() => {
    let ignore = false;
    async function fetchJobs() {
      try {
        const data = await employerService.getJobs();
        if (!ignore) {
          setJobs(Array.isArray(data) ? data : []);
        }
      } catch {
        // Ignore job loading failure
      }
    }
    fetchJobs();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    let ignore = false;
    async function fetchApplications() {
      try {
        const params = {};
        if (filterStatus) params.status = filterStatus;
        if (filterJobId) params.jobId = filterJobId;
        const data = await employerService.getApplications(params);
        if (!ignore) {
          setApplications(Array.isArray(data) ? data : []);
          setError("");
        }
      } catch (err) {
        if (!ignore) {
          setError(err?.message || "Failed to load candidate applications.");
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    fetchApplications();
    return () => {
      ignore = true;
    };
  }, [filterStatus, filterJobId]);

  async function handleSelectApp(app) {
    setSelectedApp(app);
    try {
      const freshDetail = await employerService.getApplication(app.id);
      if (freshDetail) {
        setSelectedApp(freshDetail);
      }
    } catch {
      // Fallback to list item data
    }
  }

  async function handleStatusChange(appId, newStatus) {
    setIsUpdatingStatus(true);
    setError("");
    setSuccessMessage("");
    try {
      const updated = await employerService.updateApplicationStatus(appId, newStatus);
      setApplications((prev) =>
        prev.map((a) => (a.id === appId ? { ...a, status: updated.status } : a))
      );
      if (selectedApp && selectedApp.id === appId) {
        setSelectedApp((prev) => ({ ...prev, status: updated.status }));
      }
      setSuccessMessage(`Application status updated to ${newStatus}.`);
    } catch (err) {
      setError(err?.message || "Failed to update status.");
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  function getStatusBadgeClass(status) {
    switch (status) {
      case "ACCEPTED":
      case "SHORTLISTED":
        return "status-active";
      case "REVIEWING":
      case "INTERVIEW":
        return "status-warning";
      case "REJECTED":
        return "status-error";
      default:
        return "status-inactive";
    }
  }

  return (
    <div className="applications-dashboard-container">
      {/* Header section */}
      <section className="dashboard-card" style={{ marginBottom: "1.5rem" }}>
        <h2 className="card-title">Candidate Applications Management</h2>
        <p className="card-description">
          Review candidates who have applied to your organization&apos;s job listings.
          Access candidate-authorized qualifications and voluntary disability declaration benchmarks.
        </p>

        {/* Filter bar */}
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginTop: "1rem" }}>
          <div style={{ flex: 1, minWidth: "200px" }}>
            <label htmlFor="filterJob" className="field-label" style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>
              Filter by Job
            </label>
            <select
              id="filterJob"
              value={filterJobId}
              onChange={(e) => setFilterJobId(e.target.value)}
              style={{ width: "100%", padding: "0.45rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              <option value="">All Jobs</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
          </div>

          <div style={{ flex: 1, minWidth: "200px" }}>
            <label htmlFor="filterStatus" className="field-label" style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>
              Filter by Status
            </label>
            <select
              id="filterStatus"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              style={{ width: "100%", padding: "0.45rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="alert alert-error" role="alert" style={{ marginTop: "1rem" }}>
            {error}
          </div>
        )}
        {successMessage && (
          <div className="alert alert-success" role="status" style={{ marginTop: "1rem" }}>
            {successMessage}
          </div>
        )}
      </section>

      {/* Main Grid: Application List + Detail Drawer */}
      <div style={{ display: "grid", gridTemplateColumns: selectedApp ? "1fr 1fr" : "1fr", gap: "1.5rem" }}>
        {/* Applications List */}
        <div>
          {isLoading ? (
            <p>Loading candidate applications...</p>
          ) : applications.length === 0 ? (
            <section className="dashboard-card" style={{ textAlign: "center", padding: "2.5rem" }}>
              <p style={{ color: "#64748b", fontSize: "1rem" }}>
                No candidate applications found for the selected filters.
              </p>
            </section>
          ) : (
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {applications.map((app) => {
                const isSelected = selectedApp?.id === app.id;
                return (
                  <div
                    key={app.id}
                    className="dashboard-card"
                    onClick={() => handleSelectApp(app)}
                    style={{
                      cursor: "pointer",
                      border: isSelected ? "2px solid var(--color-primary, #0284c7)" : "1px solid #e2e8f0",
                      background: isSelected ? "#f0f9ff" : "#ffffff",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                      <div>
                        <h3 style={{ fontSize: "1.05rem", fontWeight: 700, margin: 0 }}>
                          {app.candidate_name}
                        </h3>
                        <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "0.2rem 0" }}>
                          Applied for: <strong>{app.job_title}</strong>
                        </p>
                        <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                          Applied on {new Date(app.created_at).toLocaleDateString()}
                        </p>
                      </div>

                      <span className={`status-badge ${getStatusBadgeClass(app.status)}`}>
                        {app.status}
                      </span>
                    </div>

                    {app.has_declaration && (
                      <div
                        style={{
                          marginTop: "0.5rem",
                          padding: "0.25rem 0.5rem",
                          background: "#ecfdf5",
                          borderRadius: "4px",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "0.3rem",
                          fontSize: "0.78rem",
                          color: "#065f46",
                        }}
                      >
                        <span>✓</span>
                        <span>Voluntary Disability Self-Declaration On File</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Application Detail Panel */}
        {selectedApp && (
          <section className="dashboard-card" style={{ position: "sticky", top: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>
                  {selectedApp.candidate_name}
                </h3>
                <span className="field-hint" style={{ fontSize: "0.85rem" }}>
                  Role: {selectedApp.job_title}
                </span>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setSelectedApp(null)}
              >
                ✕ Close
              </button>
            </div>

            <hr style={{ border: 0, borderTop: "1px solid #e2e8f0", margin: "0.75rem 0" }} />

            {/* Candidate Contacts */}
            <div className="profile-details-list" style={{ marginBottom: "1rem" }}>
              <div className="profile-detail-item">
                <span className="detail-label">Email:</span>
                <span className="detail-value">{selectedApp.candidate_email || "Not shared"}</span>
              </div>
              <div className="profile-detail-item">
                <span className="detail-label">Phone:</span>
                <span className="detail-value">{selectedApp.candidate_phone || "Not provided"}</span>
              </div>
              <div className="profile-detail-item">
                <span className="detail-label">Application Date:</span>
                <span className="detail-value">{new Date(selectedApp.created_at).toLocaleString()}</span>
              </div>
            </div>

            {/* Candidate Cover Note */}
            {selectedApp.cover_note && (
              <div style={{ marginBottom: "1rem" }}>
                <span style={{ fontWeight: 600, fontSize: "0.9rem", display: "block", marginBottom: "0.25rem" }}>
                  Cover Note / Introduction:
                </span>
                <div style={{ padding: "0.75rem", background: "#f8fafc", borderRadius: "6px", fontSize: "0.9rem", color: "#334155" }}>
                  {selectedApp.cover_note}
                </div>
              </div>
            )}

            {/* Voluntary Disability Declaration Section */}
            <div style={{ marginBottom: "1rem", padding: "0.75rem", borderRadius: "6px", background: selectedApp.has_declaration ? "#f0fdf4" : "#f8fafc", border: `1px solid ${selectedApp.has_declaration ? "#bbf7d0" : "#e2e8f0"}` }}>
              <div style={{ fontWeight: 600, fontSize: "0.9rem", color: selectedApp.has_declaration ? "#166534" : "#64748b" }}>
                {selectedApp.has_declaration ? "♿ Voluntary Disability Declaration" : "Disability Self-Declaration"}
              </div>
              <p style={{ fontSize: "0.85rem", color: "#334155", margin: "0.25rem 0 0" }}>
                {selectedApp.has_declaration
                  ? `Candidate voluntarily declared under standard ${selectedApp.declaration_version} on ${selectedApp.declaration_accepted_at ? new Date(selectedApp.declaration_accepted_at).toLocaleDateString() : "date on file"}.`
                  : "No voluntary disability self-declaration submitted by candidate."}
              </p>
            </div>

            {/* Status Update Actions */}
            <div style={{ marginTop: "1.25rem" }}>
              <label htmlFor="updateStatusSelect" className="field-label" style={{ display: "block", fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.4rem" }}>
                Update Application Pipeline Status:
              </label>
              <select
                id="updateStatusSelect"
                value={selectedApp.status}
                onChange={(e) => handleStatusChange(selectedApp.id, e.target.value)}
                disabled={isUpdatingStatus}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontWeight: 600 }}
              >
                <option value="APPLIED">APPLIED (New Application)</option>
                <option value="REVIEWING">REVIEWING (Under Assessment)</option>
                <option value="SHORTLISTED">SHORTLISTED (Selected for Round 1)</option>
                <option value="INTERVIEW">INTERVIEW (Interview Scheduled)</option>
                <option value="ACCEPTED">ACCEPTED (Offer Extended)</option>
                <option value="REJECTED">REJECTED (Candidate Notified)</option>
              </select>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

export default ApplicationsDashboard;


import { useState, useEffect } from "react";
import employerService from "../services/employerService.js";

function JobManager({ onSelectJobForApplications }) {
  const [jobs, setJobs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Create / Edit modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingJobId, setEditingJobId] = useState(null);
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    responsibilities: "",
    requirements: "",
    location: "",
    work_mode: "Hybrid",
    status: "ACTIVE",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    setIsLoading(true);
    setError("");
    try {
      const data = await employerService.getJobs();
      setJobs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.message || "Failed to load job listings.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleOpenCreate() {
    setEditingJobId(null);
    setFormData({
      title: "",
      description: "",
      responsibilities: "",
      requirements: "",
      location: "",
      work_mode: "Hybrid",
      status: "ACTIVE",
    });
    setError("");
    setSuccessMessage("");
    setIsModalOpen(true);
  }

  async function handleOpenEdit(job) {
    setEditingJobId(job.id);
    let targetJob = job;
    try {
      const freshJob = await employerService.getJob(job.id);
      if (freshJob) targetJob = freshJob;
    } catch {
      // Fallback to table data
    }

    setFormData({
      title: targetJob.title || "",
      description: targetJob.description || "",
      responsibilities: targetJob.responsibilities || "",
      requirements: targetJob.requirements || "",
      location: targetJob.location || "",
      work_mode: targetJob.work_mode || "Hybrid",
      status: targetJob.status || "ACTIVE",
    });
    setError("");
    setSuccessMessage("");
    setIsModalOpen(true);
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!formData.title.trim()) {
      setError("Job title is required.");
      return;
    }
    if (!formData.description.trim() || formData.description.length < 10) {
      setError("Job description must contain at least 10 characters.");
      return;
    }

    setIsSubmitting(true);
    setError("");
    try {
      if (editingJobId) {
        await employerService.updateJob(editingJobId, {
          title: formData.title.trim(),
          description: formData.description.trim(),
          responsibilities: formData.responsibilities.trim() || null,
          requirements: formData.requirements.trim() || null,
          location: formData.location.trim() || null,
          work_mode: formData.work_mode,
          status: formData.status,
          is_active: formData.status === "ACTIVE",
        });
        setSuccessMessage("Job listing updated successfully.");
      } else {
        await employerService.createJob({
          title: formData.title.trim(),
          description: formData.description.trim(),
          responsibilities: formData.responsibilities.trim() || null,
          requirements: formData.requirements.trim() || null,
          location: formData.location.trim() || null,
          work_mode: formData.work_mode,
          status: formData.status,
          is_active: formData.status === "ACTIVE",
        });
        setSuccessMessage("Job listing published successfully.");
      }
      setIsModalOpen(false);
      await loadJobs();
    } catch (err) {
      setError(err?.message || "Failed to save job listing.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Are you sure you want to delete this job listing? Applications will be removed.")) return;
    try {
      await employerService.deleteJob(id);
      setSuccessMessage("Job listing deleted.");
      await loadJobs();
    } catch (err) {
      setError(err?.message || "Failed to delete job.");
    }
  }

  return (
    <div className="job-manager-container">
      {/* Header section */}
      <section className="dashboard-card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h2 className="card-title">Job Listings &amp; Recruitment Management</h2>
            <p className="card-description">
              Publish accessible job listings with transparent accommodation parameters.
              Track applications and candidate accommodation requests per role.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleOpenCreate}
          >
            + Create New Job Listing
          </button>
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

      {/* Form Modal */}
      {isModalOpen && (
        <section
          className="dashboard-card"
          style={{
            marginBottom: "1.5rem",
            border: "2px solid var(--color-primary, #0284c7)",
            background: "#f8fafc",
          }}
        >
          <h3 style={{ fontSize: "1.2rem", fontWeight: 600, marginBottom: "0.75rem" }}>
            {editingJobId ? "Edit Job Listing" : "Create New Job Listing"}
          </h3>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: "1rem" }}>
              <label htmlFor="title" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                Job Title *
              </label>
              <input
                id="title"
                name="title"
                type="text"
                placeholder="e.g. Senior Accessibility Software Engineer"
                value={formData.title}
                onChange={handleChange}
                required
                disabled={isSubmitting}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label htmlFor="work_mode" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                  Work Mode *
                </label>
                <select
                  id="work_mode"
                  name="work_mode"
                  value={formData.work_mode}
                  onChange={handleChange}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                  disabled={isSubmitting}
                >
                  <option value="Remote">Remote</option>
                  <option value="Hybrid">Hybrid</option>
                  <option value="On-site">On-site</option>
                </select>
              </div>

              <div>
                <label htmlFor="location" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                  Location / Office
                </label>
                <input
                  id="location"
                  name="location"
                  type="text"
                  placeholder="e.g. San Francisco, CA / Remote"
                  value={formData.location}
                  onChange={handleChange}
                  disabled={isSubmitting}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                />
              </div>

              <div>
                <label htmlFor="status" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                  Listing Status *
                </label>
                <select
                  id="status"
                  name="status"
                  value={formData.status}
                  onChange={handleChange}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                  disabled={isSubmitting}
                >
                  <option value="ACTIVE">ACTIVE (Accepting Applications)</option>
                  <option value="DRAFT">DRAFT (Saved as Draft)</option>
                  <option value="CLOSED">CLOSED (Closed for Applications)</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label htmlFor="description" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                Job Description &amp; Overview *
              </label>
              <textarea
                id="description"
                name="description"
                rows="4"
                placeholder="Comprehensive overview of the role, team, and company culture..."
                value={formData.description}
                onChange={handleChange}
                required
                disabled={isSubmitting}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label htmlFor="responsibilities" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                  Key Responsibilities
                </label>
                <textarea
                  id="responsibilities"
                  name="responsibilities"
                  rows="3"
                  placeholder="Bullet points or key day-to-day deliverables..."
                  value={formData.responsibilities}
                  onChange={handleChange}
                  disabled={isSubmitting}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                />
              </div>

              <div>
                <label htmlFor="requirements" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                  Required &amp; Preferred Skills
                </label>
                <textarea
                  id="requirements"
                  name="requirements"
                  rows="3"
                  placeholder="Technical competencies, assistive tech knowledge, certifications..."
                  value={formData.requirements}
                  onChange={handleChange}
                  disabled={isSubmitting}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setIsModalOpen(false)}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                {isSubmitting ? "Saving..." : editingJobId ? "Save Changes" : "Publish Job"}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Jobs List */}
      {isLoading ? (
        <p>Loading job postings...</p>
      ) : jobs.length === 0 ? (
        <section className="dashboard-card" style={{ textAlign: "center", padding: "2.5rem" }}>
          <p style={{ color: "#64748b", fontSize: "1.1rem" }}>
            No jobs posted yet.
          </p>
          <p style={{ fontSize: "0.875rem", color: "#94a3b8", marginTop: "0.5rem" }}>
            Create your first job listing to start receiving accessible applications.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: "1rem" }}
            onClick={handleOpenCreate}
          >
            Create Job
          </button>
        </section>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          {jobs.map((job) => {
            const statusClass =
              job.status === "ACTIVE"
                ? "status-active"
                : job.status === "DRAFT"
                  ? "status-warning"
                  : "status-inactive";

            return (
              <section key={job.id} className="dashboard-card" style={{ padding: "1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                      <h3 style={{ fontSize: "1.2rem", fontWeight: 700, margin: 0 }}>
                        {job.title}
                      </h3>
                      <span className={`status-badge ${statusClass}`}>
                        {job.status}
                      </span>
                      <span className="status-badge" style={{ background: "#f1f5f9", color: "#475569" }}>
                        {job.work_mode || "Hybrid"}
                      </span>
                    </div>

                    <div style={{ fontSize: "0.85rem", color: "#64748b", marginTop: "0.25rem" }}>
                      {job.location ? `📍 ${job.location} • ` : ""}
                      Posted: {new Date(job.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleOpenEdit(job)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-error btn-sm"
                      onClick={() => handleDelete(job.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>

                <p style={{ fontSize: "0.925rem", color: "#334155", margin: "0.75rem 0" }}>
                  {job.description}
                </p>

                {/* Metrics footer */}
                <div
                  style={{
                    display: "flex",
                    gap: "1.5rem",
                    borderTop: "1px solid #f1f5f9",
                    paddingTop: "0.75rem",
                    marginTop: "0.75rem",
                    fontSize: "0.875rem",
                    alignItems: "center",
                    flexWrap: "wrap",
                  }}
                >
                  <div>
                    👥 <strong>{job.applications_count || 0}</strong> Applications
                  </div>
                  <div>
                    ♿ <strong>{job.accommodation_requests_count || 0}</strong> Accommodation Requests
                  </div>
                  {onSelectJobForApplications && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ marginLeft: "auto" }}
                      onClick={() => onSelectJobForApplications(job.id)}
                    >
                      View Applications →
                    </button>
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default JobManager;


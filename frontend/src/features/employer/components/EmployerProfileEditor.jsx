import { useState } from "react";
import employerService from "../services/employerService.js";

function EmployerProfileEditor({ profile, onProfileUpdated }) {
  const [formData, setFormData] = useState({
    company_name: profile?.company_name || "",
    full_name: profile?.full_name || "",
    website: profile?.website || "",
    phone: profile?.phone || "",
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const verificationStatus = (profile?.verification_status || "PENDING").toUpperCase();
  const isVerified = verificationStatus === "VERIFIED";
  const isPending = verificationStatus === "PENDING";
  const isRejected = verificationStatus === "REJECTED";

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccessMessage("");

    if (!formData.company_name.trim()) {
      setError("Company name is required.");
      return;
    }
    if (!formData.full_name.trim()) {
      setError("Recruiter contact name is required.");
      return;
    }

    setIsLoading(true);
    try {
      const updated = await employerService.updateProfile({
        company_name: formData.company_name.trim(),
        full_name: formData.full_name.trim(),
        website: formData.website.trim() || null,
        phone: formData.phone.trim() || null,
      });
      setSuccessMessage("Company profile updated successfully.");
      if (onProfileUpdated) onProfileUpdated(updated);
    } catch (err) {
      setError(err?.message || "Failed to update profile. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="profile-editor-container">
      {/* Verification Status Banner */}
      <section
        className={`verification-banner ${
          isVerified
            ? "verification-verified"
            : isRejected
              ? "verification-rejected"
              : "verification-pending"
        }`}
        role="status"
        aria-live="polite"
        style={{ marginBottom: "1.5rem" }}
      >
        <div className="verification-badge-row">
          <span
            className={`status-badge ${
              isVerified
                ? "status-active"
                : isRejected
                  ? "status-error"
                  : "status-warning"
            }`}
          >
            Status: {verificationStatus}
          </span>
        </div>
        <h2 className="verification-heading" style={{ fontSize: "1.25rem", margin: "0.5rem 0" }}>
          {isVerified && "Organization Verified & Approved"}
          {isPending && "Organization Verification Pending Review"}
          {isRejected && "Organization Verification Requires Action"}
        </h2>
        <p className="verification-text" style={{ fontSize: "0.925rem" }}>
          {isVerified &&
            "Your organization is fully verified. Your posted jobs are publicly visible with verified inclusion badges."}
          {isPending &&
            `Your corporate email domain (${profile?.email_domain || "on file"}) is being reviewed by the NexAbility Trust & Safety team. Job postings and applications remain fully manageable during review.`}
          {isRejected &&
            "Verification could not be confirmed with the provided corporate credentials. Please contact support@nexability.org with business registration documentation."}
        </p>
      </section>

      {/* Profile Form Card */}
      <section className="dashboard-card">
        <h2 className="card-title">Organization & Recruiter Details</h2>
        <p className="card-description">
          Keep your company credentials up to date. Candidate applications and accommodation notices will route through this profile.
        </p>

        {error && (
          <div className="alert alert-error" role="alert" style={{ marginBottom: "1rem" }}>
            {error}
          </div>
        )}
        {successMessage && (
          <div className="alert alert-success" role="status" style={{ marginBottom: "1rem" }}>
            {successMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="profile-edit-form">
          <div className="form-group" style={{ marginBottom: "1rem" }}>
            <label htmlFor="company_name" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
              Company Name *
            </label>
            <input
              id="company_name"
              name="company_name"
              type="text"
              className="text-input"
              value={formData.company_name}
              onChange={handleChange}
              required
              disabled={isLoading}
              style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--color-border, #cbd5e1)" }}
            />
          </div>

          <div className="form-group" style={{ marginBottom: "1rem" }}>
            <label htmlFor="full_name" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
              Recruiter / Contact Person *
            </label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              className="text-input"
              value={formData.full_name}
              onChange={handleChange}
              required
              disabled={isLoading}
              style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--color-border, #cbd5e1)" }}
            />
          </div>

          <div className="form-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
            <div className="form-group">
              <label htmlFor="website" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                Company Website
              </label>
              <input
                id="website"
                name="website"
                type="url"
                placeholder="https://example.com"
                className="text-input"
                value={formData.website}
                onChange={handleChange}
                disabled={isLoading}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--color-border, #cbd5e1)" }}
              />
            </div>

            <div className="form-group">
              <label htmlFor="phone" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                Contact Phone
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                placeholder="+1 555-0199"
                className="text-input"
                value={formData.phone}
                onChange={handleChange}
                disabled={isLoading}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--color-border, #cbd5e1)" }}
              />
            </div>
          </div>

          <div className="form-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
            <div className="form-group">
              <span className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                Corporate Domain (Verified)
              </span>
              <div style={{ padding: "0.5rem", background: "#f8fafc", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                {profile?.email_domain || "Not provided"}
              </div>
            </div>

            <div className="form-group">
              <span className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                Account Email
              </span>
              <div style={{ padding: "0.5rem", background: "#f8fafc", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                {profile?.email || "Signed in account"}
              </div>
            </div>
          </div>

          <div className="form-actions" style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
            <button type="submit" className="btn btn-primary" disabled={isLoading}>
              {isLoading ? "Saving Changes..." : "Save Profile"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default EmployerProfileEditor;


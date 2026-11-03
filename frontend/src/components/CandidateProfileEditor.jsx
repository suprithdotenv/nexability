import { useState } from "react";
import { candidateService } from "../api/index.js";
import { useAuth } from "../context/useAuth.js";

/**
 * CandidateProfileEditor Component
 * Displays and allows editing of candidate profile (full name and phone)
 * integrates with PATCH /api/v1/candidates/me
 */
export function CandidateProfileEditor({ initialProfile, onProfileUpdated }) {
  const { user } = useAuth();
  const [profile, setProfile] = useState(
    initialProfile || {
      full_name: user?.full_name || "",
      phone: user?.phone || "",
      email: user?.email || "",
    }
  );

  const [isEditing, setIsEditing] = useState(false);
  const [fullNameInput, setFullNameInput] = useState(profile.full_name || "");
  const [phoneInput, setPhoneInput] = useState(profile.phone || "");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  function startEditing() {
    setFullNameInput(profile.full_name || "");
    setPhoneInput(profile.phone || "");
    setError("");
    setSuccessMessage("");
    setIsEditing(true);
  }

  function cancelEditing() {
    setIsEditing(false);
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccessMessage("");

    if (!fullNameInput.trim() || fullNameInput.trim().length < 2) {
      setError("Full name must be at least 2 characters.");
      return;
    }

    if (fullNameInput.trim().length > 150) {
      setError("Full name cannot exceed 150 characters.");
      return;
    }

    if (phoneInput && phoneInput.trim().length > 20) {
      setError("Phone number cannot exceed 20 characters.");
      return;
    }

    setIsLoading(true);
    try {
      const updated = await candidateService.updateProfile({
        full_name: fullNameInput.trim(),
        phone: phoneInput.trim() || null,
      });

      const nextProfile = {
        ...profile,
        full_name: updated.full_name,
        phone: updated.phone || "",
      };

      setProfile(nextProfile);
      setIsEditing(false);
      setSuccessMessage("Profile updated successfully.");

      if (onProfileUpdated) {
        onProfileUpdated(nextProfile);
      }
    } catch (err) {
      setError(err.message || "Failed to update profile. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="candidate-profile-section">
      {successMessage && (
        <div className="form-status" role="status" aria-live="polite">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="form-error" role="alert" aria-live="assertive">
          {error}
        </div>
      )}

      {!isEditing ? (
        <div className="profile-display-view">
          <div className="profile-details-list">
            <div className="profile-detail-item">
              <span className="detail-label">Full Name</span>
              <span className="detail-value">{profile.full_name || "Not provided"}</span>
            </div>
            <div className="profile-detail-item">
              <span className="detail-label">Email Address</span>
              <span className="detail-value">{profile.email || user?.email}</span>
            </div>
            <div className="profile-detail-item">
              <span className="detail-label">Phone</span>
              <span className="detail-value">{profile.phone || "Not provided"}</span>
            </div>
            <div className="profile-detail-item">
              <span className="detail-label">Account Role</span>
              <span className="status-badge status-active">Candidate</span>
            </div>
          </div>

          <div className="card-footer-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={startEditing}
              aria-label="Edit candidate profile details"
            >
              Edit Profile
            </button>
          </div>
        </div>
      ) : (
        <form className="profile-edit-form" onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="field-label" htmlFor="edit-profile-name">
              Full Name <span aria-hidden="true">*</span>
            </label>
            <input
              id="edit-profile-name"
              className="field-control"
              type="text"
              value={fullNameInput}
              onChange={(e) => setFullNameInput(e.target.value)}
              required
              minLength={2}
              maxLength={150}
              disabled={isLoading}
              aria-describedby="name-hint"
            />
            <small id="name-hint" className="field-hint">
              Between 2 and 150 characters.
            </small>
          </div>

          <div className="form-group">
            <label className="field-label" htmlFor="edit-profile-phone">
              Phone Number (optional)
            </label>
            <input
              id="edit-profile-phone"
              className="field-control"
              type="tel"
              value={phoneInput}
              onChange={(e) => setPhoneInput(e.target.value)}
              maxLength={20}
              disabled={isLoading}
              placeholder="+1 (555) 000-0000"
            />
          </div>

          <div className="auth-button-group">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading}
            >
              {isLoading ? "Saving..." : "Save Changes"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={cancelEditing}
              disabled={isLoading}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default CandidateProfileEditor;


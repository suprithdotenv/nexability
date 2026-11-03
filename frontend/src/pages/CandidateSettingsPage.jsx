import { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import { candidateService } from "../api/index.js";
import { useAuth } from "../context/useAuth.js";
import CandidateProfileEditor from "../components/CandidateProfileEditor.jsx";
import ResumeManager from "../components/ResumeManager.jsx";
import AccessibilityPreferencesManager from "../components/AccessibilityPreferencesManager.jsx";

function CandidateSettingsPage() {
  const { user } = useAuth();
  const [hasDeclaration, setHasDeclaration] = useState(false);
  const [isDeclaredInput, setIsDeclaredInput] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");

  const checkboxId = useId();
  const noteId = useId();

  // View current declaration status on mount (prevent 404 if endpoint not deployed)
  useEffect(() => {
    let isMounted = true;
    async function fetchDeclarationStatus() {
      if (!candidateService.isDeclarationSupported) {
        if (isMounted) {
          setHasDeclaration(false);
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setError("");
      try {
        const res = await candidateService.getDeclaration();
        if (isMounted && res && res.accepted) {
          setHasDeclaration(true);
          setIsDeclaredInput(true);
        }
      } catch {
        if (isMounted) {
          setHasDeclaration(false);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchDeclarationStatus();
    return () => {
      isMounted = false;
    };
  }, []);

  // Save declaration (explicit acceptance only)
  async function handleSave(event) {
    event.preventDefault();
    setError("");
    setStatusMessage("");

    if (!candidateService.isDeclarationSupported) {
      setError(
        "Candidate declaration endpoint (/api/v1/candidates/me/declaration) is awaiting backend deployment."
      );
      return;
    }

    if (!isDeclaredInput) {
      setError("Please check the declaration box before saving, or leave it unchanged.");
      return;
    }

    setIsLoading(true);
    try {
      await candidateService.saveDeclaration({
        accepted: true,
        declaration_version: "v1",
      });
      setHasDeclaration(true);
      setStatusMessage("Your voluntary disability declaration has been recorded.");
    } catch (err) {
      setError(err.message || "Failed to update declaration. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  // Withdraw declaration later via DELETE /candidates/me/declaration
  async function handleWithdraw() {
    setError("");
    setStatusMessage("");

    if (!candidateService.isDeclarationSupported) {
      setError(
        "Candidate declaration endpoint (/api/v1/candidates/me/declaration) is awaiting backend deployment."
      );
      return;
    }

    setIsLoading(true);
    try {
      await candidateService.withdrawDeclaration();
      setHasDeclaration(false);
      setIsDeclaredInput(false);
      setStatusMessage("Your voluntary disability declaration has been withdrawn.");
    } catch (err) {
      setError(err.message || "Failed to withdraw declaration. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main id="main-content" className="settings-main" tabIndex="-1">
      <div className="settings-container">
        <header className="settings-header">
          <p className="eyebrow">PROFILE &amp; PREFERENCE SETTINGS</p>
          <h1>Candidate Settings</h1>
          <p className="settings-intro">
            Manage your personal profile, active resume, voluntary accommodation preferences, and privacy settings.
          </p>
        </header>

        {/* Section 1: Candidate Profile */}
        <section className="settings-section" aria-labelledby="profile-settings-title">
          <h2 id="profile-settings-title" className="section-title">
            Personal Information
          </h2>
          <CandidateProfileEditor />
        </section>

        {/* Section 2: Resume & Documents */}
        <section className="settings-section" aria-labelledby="resume-settings-title">
          <h2 id="resume-settings-title" className="section-title">
            Resume &amp; Application Documents
          </h2>
          <p className="section-intro">
            Manage your active resume document. Inclusive employers review your qualifications and
            career experience directly through verified hiring workflows.
          </p>
          <ResumeManager />
        </section>

        {/* Section 3: Accessibility Accommodation Preferences */}
        <section className="settings-section" aria-labelledby="accessibility-settings-title">
          <h2 id="accessibility-settings-title" className="section-title">
            Accessibility &amp; Workplace Accommodations
          </h2>
          <p className="section-intro">
            Declare the tools, software, pacing, or environmental adjustments that help you succeed.
            Disclosure is strictly voluntary and never requires medical documentation.
          </p>
          <AccessibilityPreferencesManager />
        </section>

        {/* Section 4: Disability Declaration Management Section */}
        <section
          className="settings-section declaration-card"
          aria-labelledby="declaration-settings-title"
        >
          <div className="section-title-row">
            <div>
              <h2 id="declaration-settings-title" className="declaration-title">
                Voluntary Disability Self-Declaration
              </h2>
            </div>
            <span
              className={
                !candidateService.isDeclarationSupported
                  ? "status-badge status-warning"
                  : hasDeclaration
                    ? "status-badge status-active"
                    : "status-badge status-inactive"
              }
              aria-label={`Declaration status: ${
                !candidateService.isDeclarationSupported
                  ? "Awaiting Backend Support"
                  : hasDeclaration
                    ? "Active on File"
                    : "Not Declared"
              }`}
            >
              {!candidateService.isDeclarationSupported
                ? "Awaiting Backend Support"
                : hasDeclaration
                  ? "Active on File"
                  : "Not Declared"}
            </span>
          </div>

          <div
            className="declaration-info-panel"
            role="region"
            aria-label="Disability declaration details"
          >
            {!candidateService.isDeclarationSupported ? (
              <div
                className="declaration-pending-notice"
                role="status"
                style={{
                  padding: "1.25rem",
                  background: "var(--color-surface-muted)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <p style={{ margin: "0 0 0.5rem 0", fontWeight: "600", color: "var(--color-primary)" }}>
                  Backend Endpoint Pending Deployment
                </p>
                <p style={{ margin: "0", color: "var(--color-text-muted)" }}>
                  The candidate disability self-declaration endpoint (<code>/api/v1/candidates/me/declaration</code>)
                  is awaiting deployment in the backend API router. Once activated by the backend service,
                  you will be able to record, inspect, and withdraw your voluntary declaration here.
                </p>
              </div>
            ) : hasDeclaration ? (
              <div className="active-declaration-notice">
                <p>
                  You currently have a voluntary disability declaration recorded on your candidate profile.
                </p>
                <button
                  type="button"
                  className="btn btn-secondary withdraw-btn"
                  onClick={handleWithdraw}
                  disabled={isLoading}
                >
                  {isLoading ? "Withdrawing..." : "Withdraw Declaration"}
                </button>
              </div>
            ) : (
              <form className="declaration-form" onSubmit={handleSave} noValidate>
                <div className="declaration-checkbox-row">
                  <input
                    type="checkbox"
                    id={checkboxId}
                    className="declaration-checkbox"
                    checked={isDeclaredInput}
                    onChange={(e) => {
                      setIsDeclaredInput(e.target.checked);
                      setError("");
                    }}
                    aria-describedby={noteId}
                    disabled={isLoading}
                  />
                  <label htmlFor={checkboxId} className="declaration-checkbox-label">
                    <strong>I voluntarily identify as a person with a disability.</strong>
                  </label>
                </div>

                <p id={noteId} className="declaration-note">
                  This declaration is optional. You do not need to provide a medical
                  diagnosis. You can skip this step and manage your declaration later through
                  your profile settings.
                </p>

                <div className="declaration-actions">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isLoading || !isDeclaredInput}
                  >
                    {isLoading ? "Saving..." : "Save Declaration"}
                  </button>
                </div>
              </form>
            )}
          </div>

          {statusMessage ? (
            <div className="form-status" role="status" aria-live="polite">
              {statusMessage}
            </div>
          ) : null}

          {error ? (
            <div className="form-error" role="alert" aria-live="assertive">
              {error}
            </div>
          ) : null}
        </section>

        <div className="settings-footer-actions">
          <Link className="btn btn-secondary" to="/">
            Return to Home
          </Link>
          {user ? (
            <Link className="btn btn-primary" to="/candidate/dashboard">
              Candidate Dashboard
            </Link>
          ) : null}
        </div>
      </div>
    </main>
  );
}

export default CandidateSettingsPage;

import { useId, useState } from "react";
import { candidateService, tokenStore } from "../api/index.js";

/**
 * DisabilityDeclaration Component
 * Optional candidate self-declaration step adhering to NexAbility accessibility standards.
 *
 * @param {Object} props
 * @param {Function} [props.onComplete] Callback when user completes or skips (passes { declared, skipped })
 * @param {Function} [props.onBack] Callback to navigate back to previous step
 * @param {boolean} [props.isStandalone] Whether rendered standalone or in onboarding flow
 */
export function DisabilityDeclaration({ onComplete, onBack, isStandalone = false }) {
  // Functional Requirement 1: Checkbox must be unchecked by default
  const [isDeclared, setIsDeclared] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const checkboxId = useId();
  const noteId = useId();
  const titleId = useId();
  const descId = useId();

  // Functional Requirement 3: Candidate can continue after voluntarily selecting it
  async function handleContinue(event) {
    event.preventDefault();
    setError("");
    setStatusMessage("");

    // If candidate did NOT check the box, proceed without recording declaration
    if (!isDeclared) {
      if (onComplete) {
        onComplete({ declared: false, skipped: false });
      }
      return;
    }

    // Candidate voluntarily checked the box: handle according to backend support
    setIsLoading(true);
    try {
      if (candidateService.isDeclarationSupported && tokenStore.getAccessToken()) {
        await candidateService.saveDeclaration({
          accepted: true,
          declaration_version: "v1",
        });
        setStatusMessage("Your voluntary declaration has been recorded.");
        if (onComplete) {
          onComplete({ declared: true, skipped: false });
        }
      } else {
        // Backend endpoint is awaiting deployment in backend API router
        setStatusMessage(
          "Your preference has been noted for this session. Permanent database persistence for disability self-declaration is awaiting backend endpoint deployment."
        );
        if (onComplete) {
          onComplete({ declared: true, skipped: false, backendPending: true });
        }
      }
    } catch (err) {
      setError(
        err.message ||
          "Unable to record declaration at this time. You can manage this anytime in profile settings."
      );
    } finally {
      setIsLoading(false);
    }
  }

  // Functional Requirement 4: Candidate can skip without any restriction
  function handleSkip() {
    setError("");
    setStatusMessage("");
    // Do NOT send any API request when skipping
    if (onComplete) {
      onComplete({ declared: false, skipped: true });
    }
  }

  function handleBack() {
    setError("");
    setStatusMessage("");
    if (onBack) {
      onBack();
    }
  }

  return (
    <section
      className="declaration-card"
      aria-labelledby={titleId}
      aria-describedby={descId}
    >
      <header className="declaration-header">
        <p className="eyebrow">CANDIDATE ONBOARDING &bull; OPTIONAL</p>
        <h2 id={titleId} className="declaration-title">
          Help us create a more inclusive experience.
        </h2>
        <p id={descId} className="declaration-subtitle">
          We believe everyone deserves equal opportunities. You can optionally share
          this information to help us improve your experience.
        </p>
      </header>

      {/* Pale-blue information panel */}
      <div className="declaration-info-panel" role="region" aria-label="Voluntary declaration details">
        <div className="declaration-checkbox-row">
          <input
            type="checkbox"
            id={checkboxId}
            className="declaration-checkbox"
            checked={isDeclared}
            onChange={(e) => {
              // Functional Requirement 2: Candidate can select or deselect it
              setIsDeclared(e.target.checked);
              setError("");
            }}
            aria-describedby={noteId}
            disabled={isLoading}
          />
          <label htmlFor={checkboxId} className="declaration-checkbox-label">
            <strong>I voluntarily identify as a person with a disability.</strong>
          </label>
        </div>

        {/* Functional Requirement 7: Do not collect medical diagnoses */}
        <p id={noteId} className="declaration-note">
          Your declaration is completely optional. You do not need to provide a medical
          diagnosis or upload medical documents. You can skip this step and manage your
          declaration later through your profile settings.
        </p>

        {!candidateService.isDeclarationSupported && (
          <p className="declaration-backend-note" role="note" style={{ fontSize: "0.875rem", color: "var(--color-warning)", marginTop: "0.5rem" }}>
            <strong>Backend Notice:</strong> Permanent database storage for candidate declaration (<code>/api/v1/candidates/me/declaration</code>) is awaiting server deployment. Your voluntary preference is noted for this session.
          </p>
        )}

        {/* Privacy & Safeguard Pillars */}
        <ul className="declaration-safeguards" aria-label="Privacy and inclusion guarantees">
          <li>
            <span className="safeguard-icon" aria-hidden="true">&#10003;</span>
            <span><strong>Completely Voluntary:</strong> Proceed with or without declaring.</span>
          </li>
          <li>
            <span className="safeguard-icon" aria-hidden="true">&#10003;</span>
            <span><strong>No Medical Documents:</strong> Zero diagnosis paperwork needed.</span>
          </li>
          <li>
            <span className="safeguard-icon" aria-hidden="true">&#10003;</span>
            <span><strong>Privacy Protected:</strong> Never automatically shared with employers.</span>
          </li>
          <li>
            <span className="safeguard-icon" aria-hidden="true">&#10003;</span>
            <span><strong>Fully Withdrawable:</strong> Manage or delete anytime in profile settings.</span>
          </li>
        </ul>
      </div>

      {/* Screen Reader Live Announcements */}
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

      {/* Action Buttons */}
      <div className="declaration-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleContinue}
          disabled={isLoading}
        >
          {isLoading ? "Saving..." : "Continue"}
        </button>

        {!isStandalone && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleSkip}
            disabled={isLoading}
          >
            Skip for now
          </button>
        )}

        {onBack && (
          <button
            type="button"
            className="btn btn-ghost"
            onClick={handleBack}
            disabled={isLoading}
          >
            &larr; Back
          </button>
        )}
      </div>
    </section>
  );
}

export default DisabilityDeclaration;

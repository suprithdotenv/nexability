import { useEffect, useState } from "react";
import { candidateService } from "../api/index.js";

const STANDARD_CATEGORIES = [
  { value: "SCREEN_READER", label: "Screen Reader & Assistive Software" },
  { value: "CAPTIONS", label: "Captions & Communication Support" },
  { value: "MOBILITY", label: "Physical & Mobility Access" },
  { value: "TIME_AND_PACE", label: "Extended Time & Flexible Pacing" },
  { value: "REMOTE_FLEXIBILITY", label: "Remote & Schedule Flexibility" },
  { value: "VISION_ADJUSTMENT", label: "Visual Comfort & High Contrast" },
  { value: "SENSORY_ENVIRONMENT", label: "Sensory & Quiet Space" },
  { value: "OTHER", label: "Other Workplace Accommodation" },
];

/**
 * AccessibilityPreferencesManager Component
 * CRUD interface for candidate accommodation preferences.
 * Integrates with:
 * - GET /api/v1/candidates/me/accessibility
 * - POST /api/v1/candidates/me/accessibility
 * - PATCH /api/v1/candidates/me/accessibility/{id}
 * - DELETE /api/v1/candidates/me/accessibility/{id}
 */
export function AccessibilityPreferencesManager({ onPreferencesUpdated }) {
  const [preferences, setPreferences] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Add / Edit form state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [categoryInput, setCategoryInput] = useState(STANDARD_CATEGORIES[0].value);
  const [preferenceInput, setPreferenceInput] = useState("");
  const [detailsInput, setDetailsInput] = useState("");
  const [isActiveInput, setIsActiveInput] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Deletion confirmation state
  const [deletingId, setDeletingId] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Load preferences on mount
  useEffect(() => {
    let isMounted = true;
    async function loadPreferences() {
      setIsLoading(true);
      setError("");
      try {
        const list = await candidateService.getAccessibilityPreferences();
        if (isMounted) {
          setPreferences(list || []);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || "Failed to load accessibility preferences.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadPreferences();
    return () => {
      isMounted = false;
    };
  }, []);

  function getCategoryLabel(catValue) {
    const found = STANDARD_CATEGORIES.find((c) => c.value === catValue);
    return found ? found.label : catValue;
  }

  function openAddForm() {
    setEditingId(null);
    setCategoryInput(STANDARD_CATEGORIES[0].value);
    setPreferenceInput("");
    setDetailsInput("");
    setIsActiveInput(true);
    setError("");
    setSuccessMessage("");
    setIsFormOpen(true);
  }

  function openEditForm(pref) {
    setEditingId(pref.id);
    setCategoryInput(pref.category);
    setPreferenceInput(pref.preference);
    setDetailsInput(pref.details || "");
    setIsActiveInput(Boolean(pref.is_active));
    setError("");
    setSuccessMessage("");
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    setError("");
  }

  async function handleSubmitPreference(event) {
    event.preventDefault();
    setError("");
    setSuccessMessage("");

    if (!categoryInput.trim() || categoryInput.trim().length < 2) {
      setError("Please select or specify an accommodation category.");
      return;
    }

    if (!preferenceInput.trim() || preferenceInput.trim().length < 2) {
      setError("Preference title must be at least 2 characters.");
      return;
    }

    if (preferenceInput.trim().length > 150) {
      setError("Preference title cannot exceed 150 characters.");
      return;
    }

    if (detailsInput && detailsInput.trim().length > 500) {
      setError("Additional details cannot exceed 500 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingId) {
        // Update existing preference
        const updated = await candidateService.updateAccessibilityPreference(editingId, {
          category: categoryInput.trim(),
          preference: preferenceInput.trim(),
          details: detailsInput.trim() || null,
          is_active: isActiveInput,
        });

        const nextList = preferences.map((p) => (p.id === editingId ? updated : p));
        setPreferences(nextList);
        setSuccessMessage("Accessibility preference updated successfully.");
        if (onPreferencesUpdated) onPreferencesUpdated(nextList);
      } else {
        // Create new preference
        const created = await candidateService.createAccessibilityPreference({
          category: categoryInput.trim(),
          preference: preferenceInput.trim(),
          details: detailsInput.trim() || null,
          is_active: isActiveInput,
        });

        const nextList = [...preferences, created];
        setPreferences(nextList);
        setSuccessMessage("New accessibility preference added successfully.");
        if (onPreferencesUpdated) onPreferencesUpdated(nextList);
      }

      closeForm();
    } catch (err) {
      setError(err.message || "Failed to save accessibility preference.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleToggleActive(pref) {
    setError("");
    const newActiveState = !pref.is_active;

    try {
      const updated = await candidateService.updateAccessibilityPreference(pref.id, {
        is_active: newActiveState,
      });

      const nextList = preferences.map((p) => (p.id === pref.id ? updated : p));
      setPreferences(nextList);
      setSuccessMessage(
        `Preference "${pref.preference}" marked as ${newActiveState ? "Active" : "Inactive"}.`
      );
      if (onPreferencesUpdated) onPreferencesUpdated(nextList);
    } catch (err) {
      setError(err.message || "Failed to update preference status.");
    }
  }

  async function handleDeleteConfirm(id) {
    setError("");
    setSuccessMessage("");
    setIsDeleting(true);

    try {
      await candidateService.deleteAccessibilityPreference(id);
      const nextList = preferences.filter((p) => p.id !== id);
      setPreferences(nextList);
      setDeletingId(null);
      setSuccessMessage("Accessibility preference deleted successfully.");
      if (onPreferencesUpdated) onPreferencesUpdated(nextList);
    } catch (err) {
      setError(err.message || "Failed to delete accessibility preference.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="preferences-manager-component">
      {/* Voluntary Disclosure Guarantee Notice */}
      <div className="preferences-privacy-banner" role="region" aria-label="Privacy guarantee">
        <p className="privacy-banner-title">
          <span aria-hidden="true">&#128737;</span> Voluntary &amp; Privacy-First
        </p>
        <p className="privacy-banner-text">
          Declaring accommodation preferences is completely optional and protects your privacy.
          Employers only see your workplace requirements to ensure accessible interviews.
          <strong> Never include medical diagnoses or paperwork.</strong>
        </p>
      </div>

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

      {/* Add / Edit Form Modal / Panel */}
      {isFormOpen && (
        <form
          className="preference-form-panel"
          onSubmit={handleSubmitPreference}
          aria-labelledby="form-heading"
          noValidate
        >
          <h3 id="form-heading" className="form-panel-title">
            {editingId ? "Edit Accessibility Preference" : "Add Accessibility Preference"}
          </h3>

          <div className="form-group">
            <label className="field-label" htmlFor="pref-category">
              Accommodation Category <span aria-hidden="true">*</span>
            </label>
            <select
              id="pref-category"
              className="field-control"
              value={categoryInput}
              onChange={(e) => setCategoryInput(e.target.value)}
              disabled={isSubmitting}
              required
            >
              {STANDARD_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="field-label" htmlFor="pref-title">
              Preference Description <span aria-hidden="true">*</span>
            </label>
            <input
              id="pref-title"
              className="field-control"
              type="text"
              placeholder="e.g. Screen-reader compatible interview materials"
              value={preferenceInput}
              onChange={(e) => setPreferenceInput(e.target.value)}
              required
              minLength={2}
              maxLength={150}
              disabled={isSubmitting}
            />
            <small className="field-hint">Between 2 and 150 characters.</small>
          </div>

          <div className="form-group">
            <label className="field-label" htmlFor="pref-details">
              Additional Details (optional)
            </label>
            <textarea
              id="pref-details"
              className="field-control"
              rows={3}
              placeholder="Describe what works best for you (e.g. NVDA / JAWS preferred, 1.5x time on coding exercises)."
              value={detailsInput}
              onChange={(e) => setDetailsInput(e.target.value)}
              maxLength={500}
              disabled={isSubmitting}
            />
            <small className="field-hint">
              Do not provide medical diagnoses or private medical records. Maximum 500 characters.
            </small>
          </div>

          <div className="form-group checkbox-group">
            <label className="checkbox-label" htmlFor="pref-is-active">
              <input
                id="pref-is-active"
                type="checkbox"
                checked={isActiveInput}
                onChange={(e) => setIsActiveInput(e.target.checked)}
                disabled={isSubmitting}
              />
              <span>Set as Active preference for upcoming opportunities</span>
            </label>
          </div>

          <div className="auth-button-group">
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? "Saving..." : editingId ? "Update Preference" : "Add Preference"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={closeForm}
              disabled={isSubmitting}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Preferences List */}
      <div className="preferences-header-actions">
        <span className="preferences-count">
          {preferences.length === 1
            ? "1 accommodation preference declared"
            : `${preferences.length} accommodation preferences declared`}
        </span>
        {!isFormOpen && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={openAddForm}
            aria-label="Add a new accommodation preference"
          >
            + Add Accommodation
          </button>
        )}
      </div>

      {isLoading ? (
        <p className="loading-hint" role="status">
          Loading preferences...
        </p>
      ) : preferences.length === 0 ? (
        <div className="empty-preferences-box">
          <p className="empty-state-title">No accommodation preferences declared yet</p>
          <p className="empty-state-desc">
            You can declare accommodations whenever you are ready. Your choices help employers
            prepare screen readers, captions, extended time, or mobility access ahead of time.
          </p>
          {!isFormOpen && (
            <button type="button" className="btn btn-primary" onClick={openAddForm}>
              Add First Accommodation Preference
            </button>
          )}
        </div>
      ) : (
        <ul className="preferences-list" aria-label="Declared accommodation preferences">
          {preferences.map((item) => (
            <li
              key={item.id}
              className={`preference-card-item ${item.is_active ? "is-active" : "is-inactive"}`}
            >
              <div className="preference-item-header">
                <div className="preference-category-wrapper">
                  <span className="category-pill">{getCategoryLabel(item.category)}</span>
                  <span
                    className={`status-badge ${
                      item.is_active ? "status-active" : "status-inactive"
                    }`}
                  >
                    {item.is_active ? "Active" : "Paused"}
                  </span>
                </div>
                <h4 className="preference-item-title">{item.preference}</h4>
                {item.details && <p className="preference-item-details">{item.details}</p>}
              </div>

              {deletingId === item.id ? (
                <div className="delete-confirmation-box" role="alert">
                  <p>
                    Are you sure you want to delete this preference?
                  </p>
                  <div className="auth-button-group">
                    <button
                      type="button"
                      className="btn btn-error btn-sm"
                      onClick={() => handleDeleteConfirm(item.id)}
                      disabled={isDeleting}
                    >
                      {isDeleting ? "Deleting..." : "Yes, Delete"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => setDeletingId(null)}
                      disabled={isDeleting}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="preference-item-actions">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => handleToggleActive(item)}
                    aria-label={`Mark ${item.preference} as ${
                      item.is_active ? "inactive" : "active"
                    }`}
                  >
                    {item.is_active ? "Pause" : "Activate"}
                  </button>

                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => openEditForm(item)}
                    aria-label={`Edit ${item.preference}`}
                  >
                    Edit
                  </button>

                  <button
                    type="button"
                    className="btn btn-ghost btn-sm text-danger"
                    onClick={() => setDeletingId(item.id)}
                    aria-label={`Delete ${item.preference}`}
                  >
                    Delete
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default AccessibilityPreferencesManager;


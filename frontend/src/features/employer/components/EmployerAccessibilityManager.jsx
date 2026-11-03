import { useState, useEffect } from "react";
import employerService from "../services/employerService.js";

const PRESET_CATEGORIES = {
  VISUAL: {
    label: "Visual Accessibility",
    icon: "👁️",
    presets: [
      "Screen reader compatibility",
      "NVDA / JAWS support",
      "Accessible software and web interfaces (WCAG 2.2 AA)",
      "Screen magnification and high-contrast support",
    ],
  },
  MOBILITY: {
    label: "Mobility & Physical Access",
    icon: "♿",
    presets: [
      "Wheelchair-accessible building entrances",
      "Ramps and accessible elevators",
      "Accessible restrooms and washrooms",
      "Height-adjustable ergonomic workstations",
    ],
  },
  HEARING: {
    label: "Hearing & Auditory Support",
    icon: "🧏",
    presets: [
      "Live captions for virtual and in-person meetings",
      "Sign-language interpreter arrangements on request",
      "Transcripts for audio and recorded video content",
      "Visual emergency notifications and alerts",
    ],
  },
  COGNITIVE: {
    label: "Cognitive & Neurodiversity",
    icon: "🧠",
    presets: [
      "Dedicated quiet workspaces and low-sensory zones",
      "Flexible working arrangements and asynchronous communication",
      "Structured written instructions and checklists",
      "Extended time for evaluations and technical milestones",
    ],
  },
  WORKPLACE: {
    label: "Workplace & Technology Support",
    icon: "💻",
    presets: [
      "Assistive hardware stipend or direct provision",
      "Flexible schedule and core-hours autonomy",
      "Fully remote and hybrid working arrangements",
      "Confidential individual accommodation planning",
    ],
  },
};

function EmployerAccessibilityManager() {
  const [capabilities, setCapabilities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Add / Edit form state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formCategory, setFormCategory] = useState("VISUAL");
  const [formCapability, setFormCapability] = useState("");
  const [formStatus, setFormStatus] = useState("AVAILABLE");
  const [formDetails, setFormDetails] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadCapabilities();
  }, []);

  async function loadCapabilities() {
    setIsLoading(true);
    setError("");
    try {
      const data = await employerService.getAccessibilityCapabilities();
      setCapabilities(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.message || "Failed to load accessibility capabilities.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleOpenAdd(presetCategory = "VISUAL", presetName = "") {
    setEditingId(null);
    setFormCategory(presetCategory);
    setFormCapability(presetName);
    setFormStatus("AVAILABLE");
    setFormDetails("");
    setError("");
    setSuccessMessage("");
    setIsFormOpen(true);
  }

  function handleOpenEdit(cap) {
    setEditingId(cap.id);
    setFormCategory(cap.category || "VISUAL");
    setFormCapability(cap.capability || "");
    setFormStatus(cap.status || "AVAILABLE");
    setFormDetails(cap.details || "");
    setError("");
    setSuccessMessage("");
    setIsFormOpen(true);
  }

  async function handleSave(e) {
    e.preventDefault();
    if (!formCapability.trim()) {
      setError("Capability description is required.");
      return;
    }

    setIsSubmitting(true);
    setError("");
    try {
      if (editingId) {
        await employerService.updateAccessibilityCapability(editingId, {
          category: formCategory,
          capability: formCapability.trim(),
          status: formStatus,
          details: formDetails.trim() || null,
        });
        setSuccessMessage("Accessibility capability updated.");
      } else {
        await employerService.createAccessibilityCapability({
          category: formCategory,
          capability: formCapability.trim(),
          status: formStatus,
          details: formDetails.trim() || null,
        });
        setSuccessMessage("Accessibility capability added.");
      }
      setIsFormOpen(false);
      await loadCapabilities();
    } catch (err) {
      setError(err?.message || "Failed to save capability.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Remove this declared accessibility capability?")) return;
    try {
      await employerService.deleteAccessibilityCapability(id);
      setSuccessMessage("Capability removed.");
      await loadCapabilities();
    } catch (err) {
      setError(err?.message || "Failed to delete capability.");
    }
  }

  return (
    <div className="accessibility-manager-container">
      {/* Header card with inclusion note */}
      <section className="dashboard-card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h2 className="card-title">Workplace Accessibility & Accommodations Profile</h2>
            <p className="card-description" style={{ maxWidth: "700px" }}>
              Declare your organization&apos;s physical and digital accommodation facilities.
              Candidates can see these declarations to find workplaces suited to their access needs.
            </p>
            <p className="field-hint" style={{ marginTop: "0.25rem", fontStyle: "italic" }}>
              ℹ️ Notice: Declarations are self-reported by your organization. Please ensure accuracy for all workplace locations.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => handleOpenAdd()}
          >
            + Declare New Facility
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

      {/* Quick-add presets helper */}
      <section className="dashboard-card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: "600", marginBottom: "0.5rem" }}>
          Quick-Add Recommended Standards (WCAG 2.2 AA & Workplace Universal Design)
        </h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {Object.entries(PRESET_CATEGORIES).map(([catKey, cat]) => (
            <div key={catKey} style={{ display: "inline-flex", gap: "0.3rem", flexWrap: "wrap" }}>
              {cat.presets.slice(0, 2).map((preset) => {
                const alreadyAdded = capabilities.some(
                  (c) => c.capability.toLowerCase() === preset.toLowerCase()
                );
                if (alreadyAdded) return null;
                return (
                  <button
                    key={preset}
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleOpenAdd(catKey, preset)}
                    style={{ fontSize: "0.8rem", padding: "0.25rem 0.6rem" }}
                  >
                    + {preset}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </section>

      {/* Form Modal / Inline editor */}
      {isFormOpen && (
        <section
          className="dashboard-card"
          style={{
            marginBottom: "1.5rem",
            border: "2px solid var(--color-primary, #0284c7)",
            background: "#f8fafc",
          }}
        >
          <h3 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
            {editingId ? "Edit Facility Declaration" : "Declare New Accessibility Facility"}
          </h3>
          <form onSubmit={handleSave}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label htmlFor="formCategory" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                  Category *
                </label>
                <select
                  id="formCategory"
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                  disabled={isSubmitting}
                >
                  {Object.entries(PRESET_CATEGORIES).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v.icon} {v.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="formStatus" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                  Availability Status *
                </label>
                <select
                  id="formStatus"
                  value={formStatus}
                  onChange={(e) => setFormStatus(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                  disabled={isSubmitting}
                >
                  <option value="AVAILABLE">AVAILABLE (Readily available organization-wide)</option>
                  <option value="ON_REQUEST">ON_REQUEST (Available upon candidate request / arranged)</option>
                  <option value="UNAVAILABLE">UNAVAILABLE (Currently not available)</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label htmlFor="formCapability" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                Facility / Accommodation Name *
              </label>
              <input
                id="formCapability"
                type="text"
                placeholder="e.g., Screen-reader compatible internal software, Elevators with braille signage"
                value={formCapability}
                onChange={(e) => setFormCapability(e.target.value)}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                required
                disabled={isSubmitting}
              />
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label htmlFor="formDetails" className="field-label" style={{ display: "block", fontWeight: 600, marginBottom: "0.25rem" }}>
                Location, Office, or Additional Description
              </label>
              <textarea
                id="formDetails"
                rows="3"
                placeholder="Specify which locations or teams this applies to, contact person, or testing status..."
                value={formDetails}
                onChange={(e) => setFormDetails(e.target.value)}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                disabled={isSubmitting}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setIsFormOpen(false)}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                {isSubmitting ? "Saving..." : "Save Facility"}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Capabilities List Grouped by Category */}
      {isLoading ? (
        <p>Loading accessibility profile...</p>
      ) : capabilities.length === 0 ? (
        <section className="dashboard-card" style={{ textAlign: "center", padding: "2rem" }}>
          <p style={{ color: "#64748b", fontSize: "1rem" }}>
            No accessibility capabilities declared yet.
          </p>
          <p style={{ fontSize: "0.875rem", color: "#94a3b8", marginTop: "0.25rem" }}>
            Click &quot;Declare New Facility&quot; above to publish your company&apos;s accommodation standards.
          </p>
        </section>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          {capabilities.map((cap) => {
            const catInfo = PRESET_CATEGORIES[cap.category] || {
              label: cap.category,
              icon: "📌",
            };
            const statusClass =
              cap.status === "AVAILABLE"
                ? "status-active"
                : cap.status === "ON_REQUEST"
                  ? "status-warning"
                  : "status-error";

            return (
              <section
                key={cap.id}
                className="dashboard-card"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  flexWrap: "wrap",
                  gap: "1rem",
                }}
              >
                <div style={{ flex: 1, minWidth: "260px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                    <span style={{ fontSize: "1.2rem" }}>{catInfo.icon}</span>
                    <strong style={{ fontSize: "1.05rem" }}>{cap.capability}</strong>
                    <span className={`status-badge ${statusClass}`} style={{ fontSize: "0.75rem" }}>
                      {cap.status}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "#64748b", marginBottom: "0.25rem" }}>
                    Category: {catInfo.label}
                  </div>
                  {cap.details && (
                    <p style={{ fontSize: "0.9rem", color: "#334155", margin: "0.25rem 0" }}>
                      {cap.details}
                    </p>
                  )}
                  {cap.updated_at && (
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                      Last updated: {new Date(cap.updated_at).toLocaleDateString()}
                    </div>
                  )}
                </div>

                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleOpenEdit(cap)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn-error btn-sm"
                    onClick={() => handleDelete(cap.id)}
                  >
                    Delete
                  </button>
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default EmployerAccessibilityManager;


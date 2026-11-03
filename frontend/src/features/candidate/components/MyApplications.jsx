import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { candidateService } from "../../../api/index.js";

function getStatusBadgeStyle(status) {
  const s = (status || "").toUpperCase();
  switch (s) {
    case "ACCEPTED":
    case "SHORTLISTED":
      return { background: "#d1e7dd", color: "#0f5132", label: s };
    case "INTERVIEW":
    case "REVIEWING":
      return { background: "#cff4fc", color: "#055160", label: s };
    case "REJECTED":
      return { background: "#f8d7da", color: "#842029", label: s };
    case "APPLIED":
    case "SUBMITTED":
    default:
      return { background: "#e2e8f0", color: "#1e293b", label: s || "SUBMITTED" };
  }
}

export function MyApplications() {
  const [applications, setApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadApplications();
  }, []);

  async function loadApplications() {
    setIsLoading(true);
    setError("");
    try {
      const data = await candidateService.getMyApplications();
      setApplications(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.message || "Failed to load your applications.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="my-applications-section">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", margin: 0 }}>
            Track your submitted applications and hiring stages across inclusive employers.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={loadApplications}
          disabled={isLoading}
        >
          {isLoading ? "Refreshing..." : "↻ Refresh"}
        </button>
      </div>

      {error && (
        <div className="form-error" role="alert" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {isLoading && applications.length === 0 ? (
        <p>Loading your applications...</p>
      ) : applications.length === 0 ? (
        <div className="empty-state" style={{ textAlign: "center", padding: "2.5rem", background: "#ffffff", borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)" }}>
          <p style={{ fontSize: "1.125rem", fontWeight: "600", marginBottom: "0.5rem" }}>
            You haven't submitted any job applications yet.
          </p>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "1.5rem" }}>
            Explore verified inclusive positions and apply with your profile and resume.
          </p>
          <Link to="/jobs" className="btn btn-primary">
            Browse Open Positions
          </Link>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {applications.map((app) => {
            const badge = getStatusBadgeStyle(app.status);
            return (
              <article
                key={app.id}
                style={{
                  background: "#ffffff",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  padding: "1.25rem",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.5rem" }}>
                  <div>
                    <h3 style={{ fontSize: "1.125rem", margin: "0 0 0.25rem", color: "var(--color-primary)" }}>
                      <Link to={`/jobs?jobId=${app.job_posting_id}`} style={{ textDecoration: "none", color: "inherit" }}>
                        {app.job_title}
                      </Link>
                    </h3>
                    <p style={{ fontWeight: "600", color: "var(--color-text-muted)", margin: "0 0 0.5rem", fontSize: "0.9375rem" }}>
                      {app.company_name || "Verified Inclusive Employer"}
                    </p>
                  </div>
                  <span
                    style={{
                      background: badge.background,
                      color: badge.color,
                      fontSize: "0.75rem",
                      fontWeight: "bold",
                      padding: "0.25rem 0.6rem",
                      borderRadius: "999px",
                      textTransform: "uppercase",
                    }}
                  >
                    {badge.label}
                  </span>
                </div>

                <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", margin: "0.5rem 0" }}>
                  <span>Applied on {new Date(app.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}</span>
                  {app.has_declaration && (
                    <span style={{ marginLeft: "1rem", color: "var(--color-secondary)" }}>
                      ✓ Voluntary disability declaration attached
                    </span>
                  )}
                </div>

                {app.cover_note && (
                  <div style={{ background: "#f8fafc", padding: "0.75rem", borderRadius: "var(--radius-sm)", marginTop: "0.75rem", fontSize: "0.875rem" }}>
                    <p style={{ margin: "0 0 0.25rem", fontWeight: "600", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                      Submitted Cover Note:
                    </p>
                    <p style={{ margin: 0, whiteSpace: "pre-line" }}>{app.cover_note}</p>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default MyApplications;

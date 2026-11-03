import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { candidateService } from "../../../api/index.js";

function getAccStatusBadge(status) {
  const s = (status || "").toUpperCase();
  switch (s) {
    case "APPROVED":
      return { background: "#d1e7dd", color: "#0f5132", label: "Approved" };
    case "ALTERNATIVE_OFFERED":
      return { background: "#cff4fc", color: "#055160", label: "Alternative Offered" };
    case "DECLINED":
      return { background: "#f8d7da", color: "#842029", label: "Declined" };
    case "PENDING":
    default:
      return { background: "#fff3cd", color: "#664d03", label: "Awaiting Employer Response" };
  }
}

export function MyAccommodations() {
  const [accommodations, setAccommodations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadAccommodations();
  }, []);

  async function loadAccommodations() {
    setIsLoading(true);
    setError("");
    try {
      const data = await candidateService.getMyAccommodations();
      setAccommodations(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.message || "Failed to load your accommodation requests.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="my-accommodations-section">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", margin: 0 }}>
            Track the status of your workplace &amp; interview accommodation requests and view employer responses.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={loadAccommodations}
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

      {isLoading && accommodations.length === 0 ? (
        <p>Loading your accommodation requests...</p>
      ) : accommodations.length === 0 ? (
        <div className="empty-state" style={{ textAlign: "center", padding: "2.5rem", background: "#ffffff", borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)" }}>
          <p style={{ fontSize: "1.125rem", fontWeight: "600", marginBottom: "0.5rem" }}>
            No accommodation requests submitted yet.
          </p>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "1.5rem" }}>
            When viewing job openings, you can request specific facilities or arrangements directly from the job specification.
          </p>
          <Link to="/jobs" className="btn btn-primary">
            Browse Jobs &amp; Accommodations
          </Link>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {accommodations.map((acc) => {
            const badge = getAccStatusBadge(acc.status);
            return (
              <article
                key={acc.id}
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
                      Facility: {acc.facility}
                    </h3>
                    <p style={{ fontWeight: "600", color: "var(--color-text-muted)", margin: "0 0 0.25rem", fontSize: "0.9375rem" }}>
                      Position: <Link to={`/jobs?jobId=${acc.job_posting_id}`}>{acc.job_title}</Link> ({acc.company_name || "Inclusive Employer"})
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
                    }}
                  >
                    {badge.label}
                  </span>
                </div>

                <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", margin: "0.5rem 0" }}>
                  Requested on {new Date(acc.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                </p>

                {acc.description && (
                  <div style={{ background: "#f8fafc", padding: "0.75rem", borderRadius: "var(--radius-sm)", marginBottom: "0.75rem", fontSize: "0.875rem" }}>
                    <span style={{ fontWeight: "600", display: "block", fontSize: "0.75rem", color: "var(--color-text-muted)", marginBottom: "0.25rem" }}>
                      Your Request Notes:
                    </span>
                    {acc.description}
                  </div>
                )}

                {/* Employer Response Banner */}
                {acc.response_message ? (
                  <div style={{
                    background: acc.status === "APPROVED" ? "#f0fdf4" : acc.status === "DECLINED" ? "#fef2f2" : "#f0f9ff",
                    borderLeft: `4px solid ${acc.status === "APPROVED" ? "#16a34a" : acc.status === "DECLINED" ? "#dc2626" : "#0284c7"}`,
                    padding: "0.75rem 1rem",
                    borderRadius: "0 var(--radius-sm) var(--radius-sm) 0",
                    marginTop: "0.5rem",
                    fontSize: "0.875rem"
                  }}>
                    <p style={{ margin: "0 0 0.25rem", fontWeight: "700", color: "var(--color-primary)" }}>
                      Employer Response ({acc.status}):
                    </p>
                    <p style={{ margin: 0, whiteSpace: "pre-line" }}>{acc.response_message}</p>
                    <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                      Updated {new Date(acc.updated_at).toLocaleDateString()}
                    </p>
                  </div>
                ) : (
                  <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", margin: "0.25rem 0 0" }}>
                    ⏳ Awaiting employer review. You will see the employer's response here once reviewed.
                  </p>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default MyAccommodations;

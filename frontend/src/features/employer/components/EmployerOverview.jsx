import { useState, useEffect } from "react";
import employerService from "../services/employerService.js";

function EmployerOverview({ onNavigateTab }) {
  const [dashboardData, setDashboardData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let ignore = false;
    async function fetchDashboard() {
      try {
        const data = await employerService.getDashboard();
        if (!ignore) {
          setDashboardData(data);
          setError("");
        }
      } catch (err) {
        if (!ignore) {
          setError(err?.message || "Failed to load dashboard metrics.");
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    fetchDashboard();
    return () => {
      ignore = true;
    };
  }, []);

  if (isLoading) {
    return <p>Loading employer dashboard overview...</p>;
  }

  const stats = dashboardData?.stats || {};
  const recentJobs = dashboardData?.recent_jobs || [];
  const recentApps = dashboardData?.recent_applications || [];
  const recentAccs = dashboardData?.recent_accommodations || [];

  return (
    <div className="employer-overview">
      {error && (
        <div className="alert alert-error" role="alert" style={{ marginBottom: "1.5rem" }}>
          {error}
        </div>
      )}

      {/* KPI Metric Cards */}
      <div
        className="dashboard-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <div
          className="dashboard-card"
          onClick={() => onNavigateTab("jobs")}
          style={{ cursor: "pointer", transition: "transform 0.15s ease" }}
        >
          <div style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: 600 }}>ACTIVE JOBS</div>
          <div style={{ fontSize: "2rem", fontWeight: 800, color: "var(--color-primary, #0284c7)", margin: "0.25rem 0" }}>
            {stats.active_jobs || 0}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
            {stats.total_jobs || 0} Total Listings
          </div>
        </div>

        <div
          className="dashboard-card"
          onClick={() => onNavigateTab("applications")}
          style={{ cursor: "pointer", transition: "transform 0.15s ease" }}
        >
          <div style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: 600 }}>APPLICATIONS</div>
          <div style={{ fontSize: "2rem", fontWeight: 800, color: "#16a34a", margin: "0.25rem 0" }}>
            {stats.total_applications || 0}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
            {stats.pending_applications || 0} Under Initial Review
          </div>
        </div>

        <div
          className="dashboard-card"
          onClick={() => onNavigateTab("accommodations")}
          style={{ cursor: "pointer", transition: "transform 0.15s ease" }}
        >
          <div style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: 600 }}>PENDING ACCOMMODATIONS</div>
          <div style={{ fontSize: "2rem", fontWeight: 800, color: "#eab308", margin: "0.25rem 0" }}>
            {stats.pending_accommodations || 0}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
            Requires Employer Response
          </div>
        </div>

        <div
          className="dashboard-card"
          onClick={() => onNavigateTab("accessibility")}
          style={{ cursor: "pointer", transition: "transform 0.15s ease" }}
        >
          <div style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: 600 }}>ACCESSIBILITY PROFILE</div>
          <div style={{ fontSize: "2rem", fontWeight: 800, color: "#8b5cf6", margin: "0.25rem 0" }}>
            {stats.accessibility_capabilities_count || 0}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
            Declared Facilities
          </div>
        </div>
      </div>

      {/* Two Column Layout: Recent Jobs & Recent Applications */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
        {/* Recent Jobs */}
        <section className="dashboard-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <h3 className="card-title" style={{ margin: 0, fontSize: "1.1rem" }}>Recent Job Listings</h3>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigateTab("jobs")}
            >
              View All →
            </button>
          </div>

          {recentJobs.length === 0 ? (
            <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>No job postings created yet.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: "0.5rem" }}>
              {recentJobs.map((j) => (
                <li
                  key={j.id}
                  style={{
                    padding: "0.5rem 0.75rem",
                    background: "#f8fafc",
                    borderRadius: "6px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <strong>{j.title}</strong>
                    <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      {j.work_mode || "Hybrid"} • {j.applications_count || 0} Applications
                    </div>
                  </div>
                  <span className={`status-badge ${j.status === "ACTIVE" ? "status-active" : "status-inactive"}`} style={{ fontSize: "0.7rem" }}>
                    {j.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Recent Applications */}
        <section className="dashboard-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <h3 className="card-title" style={{ margin: 0, fontSize: "1.1rem" }}>Recent Applications</h3>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigateTab("applications")}
            >
              View All →
            </button>
          </div>

          {recentApps.length === 0 ? (
            <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>No candidate applications received yet.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: "0.5rem" }}>
              {recentApps.map((a) => (
                <li
                  key={a.id}
                  style={{
                    padding: "0.5rem 0.75rem",
                    background: "#f8fafc",
                    borderRadius: "6px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <strong>{a.candidate_name}</strong>
                    <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      Role: {a.job_title}
                    </div>
                  </div>
                  <span className="status-badge" style={{ fontSize: "0.7rem", background: "#e0f2fe", color: "#0369a1" }}>
                    {a.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Recent Accommodations Inbox Card */}
      <section className="dashboard-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <div>
            <h3 className="card-title" style={{ margin: 0, fontSize: "1.1rem" }}>Pending Accommodation Inquiries</h3>
            <p className="card-description" style={{ margin: "0.2rem 0 0" }}>
              Applicant accommodation requests requiring confirmation or alternative arrangements.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigateTab("accommodations")}
          >
            Manage Requests →
          </button>
        </div>

        {recentAccs.length === 0 ? (
          <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>No accommodation requests pending.</p>
        ) : (
          <div style={{ display: "grid", gap: "0.5rem" }}>
            {recentAccs.map((r) => (
              <div
                key={r.id}
                style={{
                  padding: "0.6rem 0.8rem",
                  background: "#fefce8",
                  border: "1px solid #fef08a",
                  borderRadius: "6px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <strong>{r.facility}</strong>
                  <div style={{ fontSize: "0.78rem", color: "#713f12" }}>
                    Candidate: {r.candidate_name} • Role: {r.job_title}
                  </div>
                </div>
                <span className="status-badge status-warning" style={{ fontSize: "0.7rem" }}>
                  {r.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default EmployerOverview;


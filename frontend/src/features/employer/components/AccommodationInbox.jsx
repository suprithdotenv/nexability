import { useState, useEffect } from "react";
import employerService from "../services/employerService.js";

const STATUS_OPTIONS = [
  { value: "", label: "All Requests" },
  { value: "PENDING", label: "Pending Review" },
  { value: "APPROVED", label: "Approved" },
  { value: "ALTERNATIVE_OFFERED", label: "Alternative Proposed" },
  { value: "DECLINED", label: "Declined" },
];

function AccommodationInbox() {
  const [requests, setRequests] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [filterStatus, setFilterStatus] = useState("");
  const [selectedReq, setSelectedReq] = useState(null);

  // Response form state
  const [responseStatus, setResponseStatus] = useState("APPROVED");
  const [responseMessage, setResponseMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadRequests();
  }, [filterStatus]);

  async function loadRequests() {
    setIsLoading(true);
    setError("");
    try {
      const data = await employerService.getAccommodations({ status: filterStatus });
      setRequests(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.message || "Failed to load accommodation requests.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleOpenRespond(req) {
    setSelectedReq(req);
    setResponseStatus(req.status === "PENDING" ? "APPROVED" : req.status);
    setResponseMessage(req.response_message || "");
    setError("");
    setSuccessMessage("");
  }

  async function handleSendResponse(e) {
    e.preventDefault();
    if (!selectedReq) return;

    setIsSubmitting(true);
    setError("");
    setSuccessMessage("");
    try {
      const updated = await employerService.respondToAccommodation(selectedReq.id, {
        status: responseStatus,
        response_message: responseMessage.trim() || null,
      });
      setRequests((prev) =>
        prev.map((r) => (r.id === selectedReq.id ? updated : r))
      );
      setSelectedReq(updated);
      setSuccessMessage(`Accommodation request marked as ${responseStatus}.`);
    } catch (err) {
      setError(err?.message || "Failed to update accommodation response.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function getStatusBadge(status) {
    switch (status) {
      case "APPROVED":
        return <span className="status-badge status-active">APPROVED</span>;
      case "ALTERNATIVE_OFFERED":
        return <span className="status-badge status-warning">ALTERNATIVE OFFERED</span>;
      case "DECLINED":
        return <span className="status-badge status-error">DECLINED</span>;
      default:
        return <span className="status-badge status-warning">PENDING</span>;
    }
  }

  return (
    <div className="accommodation-inbox-container">
      {/* Header section */}
      <section className="dashboard-card" style={{ marginBottom: "1.5rem" }}>
        <h2 className="card-title">Accommodation Requests Inbox</h2>
        <p className="card-description">
          Candidates can request physical, auditory, visual, or cognitive accommodations for interview and assessment rounds.
          Review and confirm reasonable workplace adjustments for each applicant.
        </p>

        {/* Filter bar */}
        <div style={{ marginTop: "1rem", maxWidth: "250px" }}>
          <label htmlFor="filterStatusSelect" className="field-label" style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>
            Filter by Request Status
          </label>
          <select
            id="filterStatusSelect"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{ width: "100%", padding: "0.45rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
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

      {/* Main Content: List + Response Form */}
      <div style={{ display: "grid", gridTemplateColumns: selectedReq ? "1fr 1fr" : "1fr", gap: "1.5rem" }}>
        {/* Requests List */}
        <div>
          {isLoading ? (
            <p>Loading accommodation requests...</p>
          ) : requests.length === 0 ? (
            <section className="dashboard-card" style={{ textAlign: "center", padding: "2.5rem" }}>
              <p style={{ color: "#64748b", fontSize: "1rem" }}>
                No accommodation requests found in this view.
              </p>
            </section>
          ) : (
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {requests.map((req) => {
                const isSelected = selectedReq?.id === req.id;
                return (
                  <div
                    key={req.id}
                    className="dashboard-card"
                    onClick={() => handleOpenRespond(req)}
                    style={{
                      cursor: "pointer",
                      border: isSelected ? "2px solid var(--color-primary, #0284c7)" : "1px solid #e2e8f0",
                      background: isSelected ? "#f0f9ff" : "#ffffff",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                      <div>
                        <h3 style={{ fontSize: "1.05rem", fontWeight: 700, margin: 0 }}>
                          {req.facility}
                        </h3>
                        <p style={{ fontSize: "0.85rem", color: "#64748b", margin: "0.2rem 0" }}>
                          Candidate: <strong>{req.candidate_name}</strong> • Role: <strong>{req.job_title}</strong>
                        </p>
                        <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                          Submitted on {new Date(req.created_at).toLocaleDateString()}
                        </p>
                      </div>

                      {getStatusBadge(req.status)}
                    </div>

                    {req.description && (
                      <p style={{ fontSize: "0.875rem", color: "#334155", margin: "0.5rem 0 0" }}>
                        &ldquo;{req.description}&rdquo;
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Response Panel */}
        {selectedReq && (
          <section className="dashboard-card" style={{ position: "sticky", top: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700, margin: 0 }}>
                  Respond to Accommodation Request
                </h3>
                <span className="field-hint" style={{ fontSize: "0.85rem" }}>
                  Candidate: {selectedReq.candidate_name} ({selectedReq.job_title})
                </span>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setSelectedReq(null)}
              >
                ✕ Close
              </button>
            </div>

            <hr style={{ border: 0, borderTop: "1px solid #e2e8f0", margin: "0.75rem 0" }} />

            <div style={{ marginBottom: "1rem" }}>
              <div style={{ fontSize: "0.85rem", color: "#64748b" }}>Requested Support:</div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, marginTop: "0.15rem" }}>
                {selectedReq.facility}
              </div>
              {selectedReq.description && (
                <div style={{ marginTop: "0.4rem", padding: "0.5rem", background: "#f8fafc", borderRadius: "4px", fontSize: "0.875rem" }}>
                  {selectedReq.description}
                </div>
              )}
            </div>

            <form onSubmit={handleSendResponse}>
              <div style={{ marginBottom: "1rem" }}>
                <label htmlFor="responseStatusSelect" className="field-label" style={{ display: "block", fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.3rem" }}>
                  Decision / Response Status *
                </label>
                <select
                  id="responseStatusSelect"
                  value={responseStatus}
                  onChange={(e) => setResponseStatus(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontWeight: 600 }}
                  disabled={isSubmitting}
                >
                  <option value="APPROVED">APPROVE (Facility will be provided)</option>
                  <option value="ALTERNATIVE_OFFERED">PROPOSE ALTERNATIVE (Offer alternative arrangement)</option>
                  <option value="DECLINED">DECLINE (Cannot reasonably provide for this stage)</option>
                </select>
              </div>

              <div style={{ marginBottom: "1rem" }}>
                <label htmlFor="responseMessageText" className="field-label" style={{ display: "block", fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.3rem" }}>
                  Response Message to Candidate
                </label>
                <textarea
                  id="responseMessageText"
                  rows="4"
                  placeholder="Provide instructions, meeting link details, software version, or reason for alternative arrangement..."
                  value={responseMessage}
                  onChange={(e) => setResponseMessage(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                  disabled={isSubmitting}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Sending..." : "Submit Response"}
                </button>
              </div>
            </form>
          </section>
        )}
      </div>
    </div>
  );
}

export default AccommodationInbox;


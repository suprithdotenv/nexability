import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { candidateService } from "../../../api/index.js";
import { useAuth } from "../../../context/useAuth.js";

const ACCESSIBILITY_STATUS_CONFIG = {
  AVAILABLE: {
    label: "Available",
    badgeClass: "badge-status-available",
    icon: "✓",
    bg: "#d1e7dd",
    color: "#0f5132",
    description: "Employer has confirmed this accommodation is active and readily provided.",
  },
  ON_REQUEST: {
    label: "Available on request",
    badgeClass: "badge-status-on-request",
    icon: "ℹ",
    bg: "#cff4fc",
    color: "#055160",
    description: "Employer provides this accommodation upon candidate request.",
  },
  NOT_SPECIFIED: {
    label: "Not specified – Inquire with employer",
    badgeClass: "badge-status-not-specified",
    icon: "?",
    bg: "#fff3cd",
    color: "#664d03",
    description: "Employer has not explicitly listed this capability. You may request clarification or accommodations.",
  },
  UNAVAILABLE: {
    label: "Unavailable",
    badgeClass: "badge-status-unavailable",
    icon: "✗",
    bg: "#f8d7da",
    color: "#842029",
    description: "Employer has noted this facility cannot currently be accommodated at this location.",
  },
};

export function InclusiveJobMatches() {
  const { user } = useAuth();
  const [matches, setMatches] = useState([]);
  const [matchCount, setMatchCount] = useState(0);
  const [rankingFormula, setRankingFormula] = useState("");
  const [status, setStatus] = useState("loading"); // "loading" | "match_found" | "no_resume" | "processing_in_progress" | "no_qualifying_matches" | "no_jobs_available" | "error"
  const [errorMessage, setErrorMessage] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [minThreshold, setMinThreshold] = useState(60.0);
  const [appliedJobIds, setAppliedJobIds] = useState(new Set());

  // Modals state
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);
  const [selectedMatchForApply, setSelectedMatchForApply] = useState(null);
  const [coverNote, setCoverNote] = useState("");
  const [isSubmittingApp, setIsSubmittingApp] = useState(false);
  const [appFeedback, setAppFeedback] = useState(null); // { type: "success" | "error", message: string }

  const [isAccModalOpen, setIsAccModalOpen] = useState(false);
  const [selectedMatchForAcc, setSelectedMatchForAcc] = useState(null);
  const [accFacility, setAccFacility] = useState("");
  const [accDescription, setAccDescription] = useState("");
  const [isSubmittingAcc, setIsSubmittingAcc] = useState(false);
  const [accFeedback, setAccFeedback] = useState(null);

  // Fetch candidate existing applications to show "Applied" state
  const loadAppliedJobs = useCallback(async () => {
    try {
      const apps = await candidateService.getMyApplications();
      if (Array.isArray(apps)) {
        setAppliedJobIds(new Set(apps.map((a) => a.job_id).filter(Boolean)));
      }
    } catch {
      // Gracefully ignore error in applications prefetch
    }
  }, []);

  const fetchMatches = useCallback(
    async (options = { forceReprocess: false }) => {
      if (options.forceReprocess) {
        setIsRefreshing(true);
      } else {
        setStatus("loading");
      }
      setErrorMessage("");

      try {
        const response = await candidateService.getMatches({
          forceReprocess: Boolean(options.forceReprocess),
          minThreshold,
        });

        if (response) {
          const list = response.top_matches || [];
          setMatches(list);
          setMatchCount(response.match_count ?? list.length);
          setRankingFormula(
            response.ranking_formula ||
              "Ranked strictly by professional compatibility (skills & experience). Accessibility evaluated independently."
          );
          setStatus(response.status || (list.length > 0 ? "match_found" : "no_qualifying_matches"));
        } else {
          setMatches([]);
          setMatchCount(0);
          setStatus("no_qualifying_matches");
        }
      } catch (err) {
        if (err.status === 404 || err.message?.includes("No active résumé found")) {
          setStatus("no_resume");
        } else if (err.status === 503) {
          setStatus("service_unavailable");
          setErrorMessage(
            "The ML matching service is currently starting up or temporarily offline. You can still browse and apply to all published jobs directly."
          );
        } else if (err.status === 502) {
          setStatus("service_unavailable");
          setErrorMessage(
            "ML pipeline communication returned a temporary gateway error. Please retry in a few moments."
          );
        } else {
          setStatus("error");
          setErrorMessage(
            err.message || "Failed to retrieve personalized job matches. Please try again."
          );
        }
      } finally {
        setIsRefreshing(false);
      }
    },
    [minThreshold]
  );

  useEffect(() => {
    let isMounted = true;
    let pollTimeout = null;

    async function initialLoad() {
      if (!isMounted) return;
      await loadAppliedJobs();
      await fetchMatches({ forceReprocess: false });
    }

    initialLoad();

    return () => {
      isMounted = false;
      if (pollTimeout) clearTimeout(pollTimeout);
    };
  }, [fetchMatches, loadAppliedJobs]);

  // Polling hook if processing is in progress
  useEffect(() => {
    let pollTimer = null;
    if (status === "processing_in_progress") {
      pollTimer = setTimeout(() => {
        fetchMatches({ forceReprocess: false });
      }, 5000);
    }
    return () => {
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [status, fetchMatches]);

  // Application submission handler
  const handleOpenApply = (match) => {
    setSelectedMatchForApply(match);
    setCoverNote("");
    setAppFeedback(null);
    setIsApplyModalOpen(true);
  };

  const handleSubmitApplication = async (e) => {
    e.preventDefault();
    if (!selectedMatchForApply) return;
    const jobId = selectedMatchForApply.job_id;
    if (!jobId) {
      setAppFeedback({
        type: "error",
        message: "No valid job identifier found for this posting. Please browse positions directly.",
      });
      return;
    }

    setIsSubmittingApp(true);
    setAppFeedback(null);

    try {
      await candidateService.applyForJob(jobId, { cover_note: coverNote });
      setAppFeedback({
        type: "success",
        message: `Successfully applied to ${selectedMatchForApply.job_title || "position"}!`,
      });
      setAppliedJobIds((prev) => new Set([...prev, jobId]));
      setTimeout(() => {
        setIsApplyModalOpen(false);
        setAppFeedback(null);
      }, 1500);
    } catch (err) {
      setAppFeedback({
        type: "error",
        message: err.message || "Could not submit application. Please try again.",
      });
    } finally {
      setIsSubmittingApp(false);
    }
  };

  // Accommodation request handler
  const handleOpenAcc = (match, presetFacility = "") => {
    setSelectedMatchForAcc(match);
    setAccFacility(presetFacility);
    setAccDescription("");
    setAccFeedback(null);
    setIsAccModalOpen(true);
  };

  const handleSubmitAccommodation = async (e) => {
    e.preventDefault();
    if (!selectedMatchForAcc) return;
    const jobId = selectedMatchForAcc.job_id;
    if (!jobId) {
      setAccFeedback({
        type: "error",
        message: "No valid job identifier found for this posting.",
      });
      return;
    }

    setIsSubmittingAcc(true);
    setAccFeedback(null);

    try {
      await candidateService.requestAccommodation(jobId, {
        facility: accFacility,
        description: accDescription,
      });
      setAccFeedback({
        type: "success",
        message: "Accommodation request sent directly to the employer's inbox.",
      });
      setTimeout(() => {
        setIsAccModalOpen(false);
        setAccFeedback(null);
      }, 1500);
    } catch (err) {
      setAccFeedback({
        type: "error",
        message: err.message || "Failed to submit accommodation request.",
      });
    } finally {
      setIsSubmittingAcc(false);
    }
  };

  return (
    <div className="inclusive-job-matches-container">
      {/* Control Bar: Threshold, Refresh, Status Info */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "1rem",
          background: "#f8fafc",
          border: "1px solid var(--color-border, #c5d7e8)",
          borderRadius: "var(--radius-md, 0.5rem)",
          padding: "1rem 1.25rem",
          marginBottom: "1.5rem",
        }}
      >
        <div>
          <span style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--color-primary, #082048)" }}>
            Professional Matching Engine:
          </span>{" "}
          <span
            style={{
              display: "inline-block",
              background: "#e0f2fe",
              color: "#0369a1",
              fontSize: "0.75rem",
              fontWeight: "700",
              padding: "0.2rem 0.5rem",
              borderRadius: "999px",
              marginLeft: "0.25rem",
            }}
          >
            Min Threshold: {minThreshold}%
          </span>
          {rankingFormula && (
            <p style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "var(--color-text-muted, #5a738e)" }}>
              {rankingFormula}
            </p>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => fetchMatches({ forceReprocess: true })}
            disabled={isRefreshing || status === "loading"}
            title="Re-run ML extraction and dense vector ranking against all current job descriptions"
          >
            {isRefreshing ? "⚡ Reprocessing ML..." : "🔄 Refresh & Re-Match"}
          </button>
          <Link to="/jobs" className="btn btn-ghost btn-sm">
            Browse All Jobs →
          </Link>
        </div>
      </div>

      {/* Main Content Areas based on Status */}
      {status === "loading" && (
        <div
          style={{
            textAlign: "center",
            padding: "3rem 1.5rem",
            background: "#ffffff",
            border: "1px solid var(--color-border, #c5d7e8)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <div
            style={{
              display: "inline-block",
              width: "2.5rem",
              height: "2.5rem",
              border: "3px solid #c5d7e8",
              borderTopColor: "var(--color-primary, #082048)",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              marginBottom: "1rem",
            }}
          />
          <h3 style={{ margin: "0 0 0.5rem", color: "var(--color-primary)" }}>
            Computing ML Professional Compatibility
          </h3>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.9375rem", maxWidth: "500px", margin: "0 auto" }}>
            Extracting candidate skills and dense 768-dimensional pgvector semantic similarities against published jobs...
          </p>
        </div>
      )}

      {status === "processing_in_progress" && (
        <div
          style={{
            padding: "2rem",
            textAlign: "center",
            background: "#f0f9ff",
            border: "1.5px solid #bae6fd",
            borderRadius: "var(--radius-md)",
          }}
        >
          <p style={{ fontSize: "1.5rem", margin: "0 0 0.5rem" }}>⚙️</p>
          <h3 style={{ margin: "0 0 0.5rem", color: "#0369a1" }}>Résumé Processing In Progress</h3>
          <p style={{ color: "#0c4a6e", fontSize: "0.9375rem", maxWidth: "550px", margin: "0 auto 1rem" }}>
            The ML pipeline is currently parsing your document, generating dense embeddings, and computing compatibility.
            This page will refresh automatically every 5 seconds.
          </p>
          <span style={{ fontSize: "0.8125rem", color: "#0284c7" }}>Polling matching pipeline...</span>
        </div>
      )}

      {status === "no_resume" && (
        <div
          style={{
            padding: "2.5rem",
            textAlign: "center",
            background: "#fffbeb",
            border: "1.5px solid #fde68a",
            borderRadius: "var(--radius-md)",
          }}
        >
          <p style={{ fontSize: "2rem", margin: "0 0 0.5rem" }}>📄</p>
          <h3 style={{ margin: "0 0 0.5rem", color: "#92400e" }}>No Active Résumé Found</h3>
          <p style={{ color: "#78350f", fontSize: "0.9375rem", maxWidth: "500px", margin: "0 auto 1.25rem" }}>
            To unlock AI-powered professional compatibility matching and personalized recommendations, please upload your
            résumé in the <strong>Resume &amp; Documents</strong> section above.
          </p>
          <a href="#card-resume-title" className="btn btn-primary">
            Upload Résumé Now
          </a>
        </div>
      )}

      {status === "no_qualifying_matches" && (
        <div
          style={{
            padding: "2.5rem",
            textAlign: "center",
            background: "#f8fafc",
            border: "1px solid var(--color-border, #c5d7e8)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <p style={{ fontSize: "2rem", margin: "0 0 0.5rem" }}>🎯</p>
          <h3 style={{ margin: "0 0 0.5rem", color: "var(--color-primary)" }}>
            No Qualifying Matches Above {minThreshold}%
          </h3>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.9375rem", maxWidth: "550px", margin: "0 auto 1.25rem" }}>
            We uphold strict matching standards: only positions meeting or exceeding the 60% professional compatibility
            threshold are presented. As employers publish new opportunities matching your qualifications, they will appear here.
          </p>
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setMinThreshold(40.0);
                fetchMatches({ forceReprocess: false });
              }}
            >
              Show Matches at 40%+
            </button>
            <Link to="/jobs" className="btn btn-primary">
              Explore All Open Positions
            </Link>
          </div>
        </div>
      )}

      {status === "no_jobs_available" && (
        <div
          style={{
            padding: "2.5rem",
            textAlign: "center",
            background: "#f8fafc",
            border: "1px solid var(--color-border, #c5d7e8)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <p style={{ fontSize: "2rem", margin: "0 0 0.5rem" }}>💼</p>
          <h3 style={{ margin: "0 0 0.5rem", color: "var(--color-primary)" }}>No Active Job Openings</h3>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.9375rem" }}>
            There are currently no published positions in the system. Check back soon!
          </p>
        </div>
      )}

      {status === "service_unavailable" && (
        <div
          style={{
            padding: "2rem",
            background: "#fff8f6",
            border: "1.5px solid #fecaca",
            borderRadius: "var(--radius-md)",
            marginBottom: "1.5rem",
          }}
        >
          <h3 style={{ margin: "0 0 0.5rem", color: "#991b1b" }}>ML Matching Service Offline</h3>
          <p style={{ color: "#7f1d1d", fontSize: "0.9375rem", margin: "0 0 1rem" }}>{errorMessage}</p>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => fetchMatches({ forceReprocess: false })}
            >
              Retry Connection
            </button>
            <Link to="/jobs" className="btn btn-primary btn-sm">
              View All Positions Directly
            </Link>
          </div>
        </div>
      )}

      {status === "error" && (
        <div
          style={{
            padding: "2rem",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "var(--radius-md)",
            marginBottom: "1.5rem",
          }}
        >
          <h3 style={{ margin: "0 0 0.5rem", color: "#991b1b" }}>Error Loading Matches</h3>
          <p style={{ color: "#7f1d1d", fontSize: "0.9375rem", margin: "0 0 1rem" }}>{errorMessage}</p>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => fetchMatches({ forceReprocess: false })}
          >
            Retry
          </button>
        </div>
      )}

      {/* MATCHES LIST */}
      {status === "match_found" && matches.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <p style={{ margin: 0, fontSize: "0.9375rem", color: "var(--color-text-muted)" }}>
              Found <strong>{matchCount}</strong> qualifying position{matchCount === 1 ? "" : "s"} ranked by compatibility:
            </p>
          </div>

          {matches.map((match) => {
            const companyName = match.company_info?.company_name || "Verified Inclusive Employer";
            const jobTitle = match.job_title || match.job_info?.job_title || "Published Role";
            const matchScore = Math.round(match.professional_match_score || 0);
            const isApplied = match.job_id && appliedJobIds.has(match.job_id);

            // Extract skills from match
            const skillsMatched =
              match.professional_match?.skills_matched ||
              match.professional_match?.matched_skills ||
              match.job_info?.required_skills ||
              [];

            // Extract requirements evaluated
            const reqs = match.accessibility_requirements || [];

            return (
              <article
                key={match.job_id || match.rank}
                style={{
                  background: "#ffffff",
                  border: "1.5px solid var(--color-border, #c5d7e8)",
                  borderRadius: "var(--radius-lg, 0.75rem)",
                  padding: "1.5rem",
                  boxShadow: "0 2px 8px rgba(8, 32, 72, 0.04)",
                  transition: "transform 0.15s ease, box-shadow 0.15s ease",
                }}
              >
                {/* Header row: Rank, Title, Company & Score Badge */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: "1rem",
                    borderBottom: "1px solid var(--color-border, #e2e8f0)",
                    paddingBottom: "1rem",
                    marginBottom: "1rem",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                      <span
                        style={{
                          background: "var(--color-primary, #082048)",
                          color: "#ffffff",
                          fontWeight: "800",
                          fontSize: "0.75rem",
                          padding: "0.2rem 0.55rem",
                          borderRadius: "999px",
                          letterSpacing: "0.05em",
                        }}
                      >
                        RANK #{match.rank}
                      </span>
                      {match.company_info?.verification_status === "VERIFIED" && (
                        <span
                          style={{
                            background: "#ecfdf5",
                            color: "#065f46",
                            fontSize: "0.75rem",
                            fontWeight: "700",
                            padding: "0.15rem 0.5rem",
                            borderRadius: "999px",
                            border: "1px solid #a7f3d0",
                          }}
                        >
                          ✓ Verified Employer
                        </span>
                      )}
                    </div>

                    <h3 style={{ margin: "0.25rem 0 0.25rem", fontSize: "1.35rem", color: "var(--color-primary)" }}>
                      {jobTitle}
                    </h3>
                    <p style={{ margin: 0, fontSize: "1rem", fontWeight: "600", color: "#334155" }}>
                      🏢 {companyName}
                    </p>
                  </div>

                  {/* Prominent Match Score Block */}
                  <div
                    style={{
                      textAlign: "right",
                      background: matchScore >= 75 ? "#f0fdf4" : "#f8fafc",
                      border: matchScore >= 75 ? "1.5px solid #86efac" : "1.5px solid #cbd5e1",
                      borderRadius: "var(--radius-md)",
                      padding: "0.75rem 1.25rem",
                      minWidth: "160px",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "1.75rem",
                        fontWeight: "900",
                        color: matchScore >= 75 ? "#166534" : "var(--color-primary)",
                        lineHeight: 1,
                      }}
                    >
                      {matchScore}%
                    </div>
                    <div style={{ fontSize: "0.75rem", fontWeight: "700", color: "#475569", marginTop: "0.25rem" }}>
                      Professional Match
                    </div>
                    <div style={{ fontSize: "0.6875rem", color: "#64748b", marginTop: "0.15rem" }}>
                      Exceeds 60% threshold
                    </div>
                  </div>
                </div>

                {/* Job Overview if available */}
                {match.job_info?.overview && (
                  <p style={{ fontSize: "0.9375rem", color: "#334155", margin: "0 0 1rem", lineHeight: "1.5" }}>
                    {match.job_info.overview}
                  </p>
                )}

                {/* Professional Qualifications & Skills */}
                {skillsMatched.length > 0 && (
                  <div style={{ marginBottom: "1.25rem" }}>
                    <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.875rem", color: "var(--color-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      🎯 Matched Professional Competencies &amp; Skills
                    </h4>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                      {skillsMatched.map((skill, idx) => (
                        <span
                          key={idx}
                          style={{
                            background: "#eef2ff",
                            color: "#3730a3",
                            border: "1px solid #c7d2fe",
                            borderRadius: "var(--radius-sm, 0.25rem)",
                            padding: "0.25rem 0.6rem",
                            fontSize: "0.8125rem",
                            fontWeight: "600",
                          }}
                        >
                          ✓ {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Accessibility Compatibility Section (Separated & Non-penalizing) */}
                <div
                  style={{
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    borderRadius: "var(--radius-md)",
                    padding: "1rem",
                    marginBottom: "1.25rem",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.5rem" }}>
                    <h4 style={{ margin: 0, fontSize: "0.9375rem", color: "var(--color-primary)" }}>
                      ♿ Workplace Accessibility &amp; Accommodations
                    </h4>
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      Evaluated independently • Never reduces professional score
                    </span>
                  </div>

                  {reqs.length > 0 ? (
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
                        <thead>
                          <tr style={{ textAlign: "left", color: "#475569", borderBottom: "1px solid #cbd5e1" }}>
                            <th style={{ padding: "0.4rem 0.5rem" }}>Your Declared Need</th>
                            <th style={{ padding: "0.4rem 0.5rem" }}>Employer Status</th>
                            <th style={{ padding: "0.4rem 0.5rem" }}>Employer Capability Notes</th>
                            <th style={{ padding: "0.4rem 0.5rem", textAlign: "right" }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reqs.map((req, rIdx) => {
                            const statKey = req.employer_status || "NOT_SPECIFIED";
                            const cfg = ACCESSIBILITY_STATUS_CONFIG[statKey] || ACCESSIBILITY_STATUS_CONFIG.NOT_SPECIFIED;

                            return (
                              <tr key={rIdx} style={{ borderBottom: "1px solid #f1f5f9" }}>
                                <td style={{ padding: "0.5rem", fontWeight: "600", color: "#1e293b" }}>
                                  {req.preference}
                                </td>
                                <td style={{ padding: "0.5rem", whiteSpace: "nowrap" }}>
                                  <span
                                    style={{
                                      display: "inline-block",
                                      background: cfg.bg,
                                      color: cfg.color,
                                      padding: "0.15rem 0.5rem",
                                      borderRadius: "999px",
                                      fontWeight: "700",
                                      fontSize: "0.75rem",
                                    }}
                                  >
                                    {cfg.icon} {cfg.label}
                                  </span>
                                </td>
                                <td style={{ padding: "0.5rem", color: "#475569" }}>
                                  {req.employer_capability || req.details || cfg.description}
                                </td>
                                <td style={{ padding: "0.5rem", textAlign: "right", whiteSpace: "nowrap" }}>
                                  {(req.can_request || req.is_gap) && (
                                    <button
                                      type="button"
                                      className="btn btn-secondary btn-sm"
                                      style={{ fontSize: "0.75rem", padding: "0.2rem 0.5rem" }}
                                      onClick={() => handleOpenAcc(match, req.preference)}
                                    >
                                      Request
                                    </button>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.875rem", color: "#475569" }}>
                      <span>
                        Employer supports standard inclusive accommodation requests upon candidate inquiry.
                      </span>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        style={{ fontSize: "0.8125rem" }}
                        onClick={() => handleOpenAcc(match, "")}
                      >
                        + Request Accommodation
                      </button>
                    </div>
                  )}
                </div>

                {/* Footer Actions: Apply & Request Accommodation */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    alignItems: "center",
                    gap: "0.75rem",
                    flexWrap: "wrap",
                  }}
                >
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => handleOpenAcc(match, "")}
                  >
                    Request Accommodation
                  </button>

                  {isApplied ? (
                    <button type="button" className="btn btn-secondary" disabled>
                      ✓ Already Applied
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => handleOpenApply(match)}
                    >
                      Apply for Position
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* APPLICATION MODAL */}
      {isApplyModalOpen && selectedMatchForApply && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="apply-modal-title"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(8, 32, 72, 0.6)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            padding: "1rem",
            zIndex: 1000,
          }}
        >
          <div
            className="modal-content"
            style={{
              background: "#ffffff",
              borderRadius: "var(--radius-lg, 1rem)",
              padding: "2rem",
              maxWidth: "520px",
              width: "100%",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <h2 id="apply-modal-title" style={{ marginTop: 0, color: "var(--color-primary)" }}>
              Submit Job Application
            </h2>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", margin: "0 0 1rem" }}>
              Role: <strong>{selectedMatchForApply.job_title}</strong> at{" "}
              {selectedMatchForApply.company_info?.company_name}
            </p>

            {appFeedback && (
              <div
                className={appFeedback.type === "success" ? "form-status" : "form-error"}
                role="alert"
                style={{ marginBottom: "1rem" }}
              >
                {appFeedback.message}
              </div>
            )}

            <form onSubmit={handleSubmitApplication}>
              <div
                style={{
                  background: "#f0f9ff",
                  padding: "0.75rem 1rem",
                  borderRadius: "var(--radius-sm)",
                  marginBottom: "1rem",
                  fontSize: "0.875rem",
                }}
              >
                <p style={{ margin: "0 0 0.25rem" }}>
                  Applicant: <strong>{user?.full_name || user?.email}</strong>
                </p>
                <p style={{ margin: 0, color: "var(--color-success)" }}>
                  ✓ Match Score: {Math.round(selectedMatchForApply.professional_match_score || 0)}%
                </p>
              </div>

              <div className="field-group" style={{ marginBottom: "1.25rem" }}>
                <label
                  htmlFor="match-apply-cover-note"
                  style={{ display: "block", fontWeight: "600", marginBottom: "0.4rem" }}
                >
                  Cover Note / Message for Hiring Team (Optional)
                </label>
                <textarea
                  id="match-apply-cover-note"
                  rows="4"
                  maxLength={2000}
                  placeholder="Introduce yourself and highlight relevant competencies..."
                  value={coverNote}
                  onChange={(e) => setCoverNote(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border)",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsApplyModalOpen(false)}
                  disabled={isSubmittingApp}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmittingApp}>
                  {isSubmittingApp ? "Submitting..." : "Confirm Application"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ACCOMMODATION REQUEST MODAL */}
      {isAccModalOpen && selectedMatchForAcc && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="acc-modal-title"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(8, 32, 72, 0.6)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            padding: "1rem",
            zIndex: 1000,
          }}
        >
          <div
            className="modal-content"
            style={{
              background: "#ffffff",
              borderRadius: "var(--radius-lg, 1rem)",
              padding: "2rem",
              maxWidth: "520px",
              width: "100%",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <h2 id="acc-modal-title" style={{ marginTop: 0, color: "var(--color-primary)" }}>
              Request Workplace Accommodation
            </h2>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", margin: "0 0 1rem" }}>
              For position: <strong>{selectedMatchForAcc.job_title}</strong> at{" "}
              {selectedMatchForAcc.company_info?.company_name}
            </p>

            {accFeedback && (
              <div
                className={accFeedback.type === "success" ? "form-status" : "form-error"}
                role="alert"
                style={{ marginBottom: "1rem" }}
              >
                {accFeedback.message}
              </div>
            )}

            <form onSubmit={handleSubmitAccommodation}>
              <div className="field-group" style={{ marginBottom: "1rem" }}>
                <label
                  htmlFor="match-acc-facility"
                  style={{ display: "block", fontWeight: "600", marginBottom: "0.4rem" }}
                >
                  Accommodation or Facility Name *
                </label>
                <input
                  id="match-acc-facility"
                  type="text"
                  required
                  placeholder="e.g. Ergonomic workstation, Screen reader test, Quiet interview space..."
                  value={accFacility}
                  onChange={(e) => setAccFacility(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border)",
                  }}
                />
              </div>

              <div className="field-group" style={{ marginBottom: "1.25rem" }}>
                <label
                  htmlFor="match-acc-description"
                  style={{ display: "block", fontWeight: "600", marginBottom: "0.4rem" }}
                >
                  Details or Context (Optional)
                </label>
                <textarea
                  id="match-acc-description"
                  rows="3"
                  maxLength={1000}
                  placeholder="Describe your preference or details so the employer can prepare effectively..."
                  value={accDescription}
                  onChange={(e) => setAccDescription(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border)",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsAccModalOpen(false)}
                  disabled={isSubmittingAcc}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmittingAcc}>
                  {isSubmittingAcc ? "Sending Request..." : "Send Request to Employer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default InclusiveJobMatches;

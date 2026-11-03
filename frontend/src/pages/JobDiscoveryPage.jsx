import { useState, useEffect, useId } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { candidateService } from "../api/index.js";
import { useAuth } from "../context/useAuth.js";
import {
  calculateProfessionalMatch,
  evaluateAccessibilityCompatibility,
} from "../utils/matching.js";

export function JobDiscoveryPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedJobIdParam = searchParams.get("jobId");

  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [candidatePrefs, setCandidatePrefs] = useState([]);
  const [candidateResume, setCandidateResume] = useState(null);
  const [candidateApplications, setCandidateApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedWorkMode, setSelectedWorkMode] = useState("ALL");
  const [selectedLocation, setSelectedLocation] = useState("ALL");
  const [facilityFilter, setFacilityFilter] = useState("ALL");

  // Application Modal state
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);
  const [coverNote, setCoverNote] = useState("");
  const [isSubmittingApp, setIsSubmittingApp] = useState(false);
  const [appSuccessMessage, setAppSuccessMessage] = useState("");
  const [appError, setAppError] = useState("");

  // Accommodation Request Modal state
  const [isAccModalOpen, setIsAccModalOpen] = useState(false);
  const [accFacility, setAccFacility] = useState("");
  const [accDescription, setAccDescription] = useState("");
  const [isSubmittingAcc, setIsSubmittingAcc] = useState(false);
  const [accSuccessMessage, setAccSuccessMessage] = useState("");
  const [accError, setAccError] = useState("");

  const searchInputId = useId();

  // Load public jobs and candidate context
  useEffect(() => {
    let ignore = false;
    async function fetchAllData() {
      try {
        const jobsData = await candidateService.getJobs();
        const jobList = Array.isArray(jobsData) ? jobsData : [];
        if (!ignore) {
          setJobs(jobList);
          setError("");
        }

        // Auto-select job if jobId param provided or pick first job
        if (jobList.length > 0 && !ignore) {
          const found = selectedJobIdParam
            ? jobList.find((j) => String(j.id) === String(selectedJobIdParam))
            : jobList[0];
          setSelectedJob(found || jobList[0]);
        }

        // If candidate is logged in, load accessibility preferences, resume & existing applications
        const userRole = (user?.role || "").toLowerCase();
        if (user && userRole === "candidate" && !ignore) {
          try {
            const [prefs, resume, apps] = await Promise.allSettled([
              candidateService.getAccessibilityPreferences(),
              candidateService.getResume(),
              candidateService.getMyApplications(),
            ]);

            if (!ignore) {
              if (prefs.status === "fulfilled" && Array.isArray(prefs.value)) {
                setCandidatePrefs(prefs.value);
              }
              if (resume.status === "fulfilled") {
                setCandidateResume(resume.value);
              }
              if (apps.status === "fulfilled" && Array.isArray(apps.value)) {
                setCandidateApplications(apps.value);
              }
            }
          } catch {
            // Gracefully continue with available info
          }
        }
      } catch (err) {
        if (!ignore) {
          setError(err?.message || "Failed to load job listings from server.");
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    fetchAllData();
    return () => {
      ignore = true;
    };
  }, [selectedJobIdParam, user]);

  // Handle job card selection
  async function handleSelectJob(job) {
    setSelectedJob(job);
    setSearchParams({ jobId: job.id });
    setAppSuccessMessage("");
    setAppError("");
    setAccSuccessMessage("");
    setAccError("");

    // Fetch single job details to ensure full capabilities and descriptions are fresh
    try {
      const detailed = await candidateService.getJob(job.id);
      if (detailed) {
        setSelectedJob(detailed);
      }
    } catch {
      // Keep selected job
    }
  }

  // Filter calculations
  const locations = Array.from(
    new Set(jobs.map((j) => j.location).filter(Boolean))
  );

  const filteredJobs = jobs.filter((job) => {
    // 1. Text Search (Title, Description, Company, Requirements)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchText = `${job.title} ${job.company_name || ""} ${job.location || ""} ${job.description || ""} ${job.requirements || ""}`.toLowerCase();
      if (!matchText.includes(q)) return false;
    }

    // 2. Work Mode
    if (selectedWorkMode !== "ALL") {
      if ((job.work_mode || "").toUpperCase() !== selectedWorkMode.toUpperCase()) {
        return false;
      }
    }

    // 3. Location
    if (selectedLocation !== "ALL") {
      if ((job.location || "").toLowerCase() !== selectedLocation.toLowerCase()) {
        return false;
      }
    }

    // 4. Accessibility Facility
    if (facilityFilter !== "ALL") {
      const caps = job.accessibility_capabilities || [];
      const hasCap = caps.some(
        (c) =>
          c.capability?.toLowerCase().includes(facilityFilter.toLowerCase()) ||
          c.category?.toLowerCase().includes(facilityFilter.toLowerCase())
      );
      if (!hasCap) return false;
    }

    return true;
  });

  // Candidate evaluation data for selected job
  const candidateContext = user
    ? {
        full_name: user.full_name,
        has_resume: Boolean(candidateResume),
        resume_filename: candidateResume?.original_filename || null,
      }
    : null;

  const profMatch = calculateProfessionalMatch(selectedJob, candidateContext);
  const accessEval = evaluateAccessibilityCompatibility(
    candidatePrefs,
    selectedJob?.accessibility_capabilities || []
  );

  const alreadyApplied = candidateApplications.some(
    (a) => String(a.job_posting_id) === String(selectedJob?.id)
  );

  // Submit Application
  async function handleSubmitApplication(e) {
    e.preventDefault();
    if (!selectedJob) return;
    setIsSubmittingApp(true);
    setAppError("");
    setAppSuccessMessage("");

    try {
      const res = await candidateService.applyForJob(selectedJob.id, {
        cover_note: coverNote,
      });
      setAppSuccessMessage(
        `Application submitted successfully! Application reference #${res.id.slice(0, 8)}.`
      );
      setCandidateApplications((prev) => [...prev, res]);
      setIsApplyModalOpen(false);
      setCoverNote("");
    } catch (err) {
      setAppError(err.message || "Failed to submit job application.");
    } finally {
      setIsSubmittingApp(false);
    }
  }

  // Submit Accommodation Request
  async function handleSubmitAccommodation(e) {
    e.preventDefault();
    if (!selectedJob) return;
    if (!accFacility.trim()) {
      setAccError("Please enter the accommodation or facility name.");
      return;
    }

    setIsSubmittingAcc(true);
    setAccError("");
    setAccSuccessMessage("");

    try {
      await candidateService.requestAccommodation(selectedJob.id, {
        facility: accFacility.trim(),
        description: accDescription.trim() || null,
      });
      setAccSuccessMessage(
        `Accommodation request for "${accFacility.trim()}" has been sent to the employer.`
      );
      setIsAccModalOpen(false);
      setAccFacility("");
      setAccDescription("");
    } catch (err) {
      setAccError(err.message || "Failed to submit accommodation request.");
    } finally {
      setIsSubmittingAcc(false);
    }
  }

  function handleOpenAccommodationModal(initialFacility = "") {
    setAccFacility(initialFacility);
    setAccDescription("");
    setAccError("");
    setAccSuccessMessage("");
    setIsAccModalOpen(true);
  }

  return (
    <main id="main-content" className="job-discovery-main" tabIndex="-1" style={{ padding: "1.5rem", maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header */}
      <header className="page-header" style={{ marginBottom: "1.5rem" }}>
        <p className="eyebrow">INCLUSIVE OPPORTUNITIES</p>
        <h1>Discover Open Positions</h1>
        <p className="page-intro">
          Explore job opportunities with verified inclusive employers. Review job requirements, separate professional match scoring, and verified workplace accessibility capabilities.
        </p>
      </header>

      {/* Global Alerts */}
      {error && (
        <div className="form-error" role="alert" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      {appSuccessMessage && (
        <div className="form-status" role="status" style={{ marginBottom: "1rem" }}>
          ✓ {appSuccessMessage} &bull; <Link to="/candidate/dashboard">View My Applications</Link>
        </div>
      )}
      {accSuccessMessage && (
        <div className="form-status" role="status" style={{ marginBottom: "1rem" }}>
          ✓ {accSuccessMessage} &bull; <Link to="/candidate/dashboard">View My Accommodation Requests</Link>
        </div>
      )}

      {/* Search and Filters Bar */}
      <section className="search-filters-bar" aria-label="Job search and filters" style={{
        background: "var(--color-surface, #ffffff)",
        padding: "1.25rem",
        borderRadius: "var(--radius-md, 0.75rem)",
        border: "1px solid var(--color-border, #c5d7e8)",
        marginBottom: "1.5rem",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "1rem",
        alignItems: "end"
      }}>
        {/* Keyword Search */}
        <div>
          <label htmlFor={searchInputId} style={{ display: "block", fontSize: "0.875rem", fontWeight: "600", marginBottom: "0.4rem" }}>
            Search Keywords
          </label>
          <input
            id={searchInputId}
            type="search"
            placeholder="Title, skills, company..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}
          />
        </div>

        {/* Work Mode */}
        <div>
          <label htmlFor="filter-work-mode" style={{ display: "block", fontSize: "0.875rem", fontWeight: "600", marginBottom: "0.4rem" }}>
            Work Arrangement
          </label>
          <select
            id="filter-work-mode"
            value={selectedWorkMode}
            onChange={(e) => setSelectedWorkMode(e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}
          >
            <option value="ALL">All Modes</option>
            <option value="Remote">Remote</option>
            <option value="Hybrid">Hybrid</option>
            <option value="On-site">On-site</option>
          </select>
        </div>

        {/* Location */}
        <div>
          <label htmlFor="filter-location" style={{ display: "block", fontSize: "0.875rem", fontWeight: "600", marginBottom: "0.4rem" }}>
            Location
          </label>
          <select
            id="filter-location"
            value={selectedLocation}
            onChange={(e) => setSelectedLocation(e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}
          >
            <option value="ALL">All Locations</option>
            {locations.map((loc) => (
              <option key={loc} value={loc}>
                {loc}
              </option>
            ))}
          </select>
        </div>

        {/* Accessibility Facilities Filter */}
        <div>
          <label htmlFor="filter-facility" style={{ display: "block", fontSize: "0.875rem", fontWeight: "600", marginBottom: "0.4rem" }}>
            Accessibility Facility
          </label>
          <select
            id="filter-facility"
            value={facilityFilter}
            onChange={(e) => setFacilityFilter(e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}
          >
            <option value="ALL">All Facilities</option>
            <option value="Screen Reader">Screen Reader Ready</option>
            <option value="Wheelchair">Step-Free / Wheelchair</option>
            <option value="Captions">Captions / Subtitles</option>
            <option value="Quiet">Quiet Workspace</option>
            <option value="Flexible">Flexible Schedule</option>
            <option value="Assistive">Assistive Technology</option>
          </select>
        </div>
      </section>

      {/* Main Two-Column Layout */}
      {isLoading ? (
        <div style={{ textAlign: "center", padding: "3rem" }}>
          <p>Loading available job postings from backend...</p>
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="empty-state" style={{ textAlign: "center", padding: "3rem", background: "#fff", borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)" }}>
          <h3>No matching positions found</h3>
          <p>Try clearing or modifying your search filters above to view other inclusive positions.</p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setSearchQuery("");
              setSelectedWorkMode("ALL");
              setSelectedLocation("ALL");
              setFacilityFilter("ALL");
            }}
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="discovery-layout" style={{ display: "grid", gridTemplateColumns: "minmax(300px, 1fr) minmax(400px, 1.6fr)", gap: "1.5rem", alignItems: "start" }}>
          {/* Left Column: Job Cards List */}
          <div className="job-list-column" style={{ display: "flex", flexDirection: "column", gap: "1rem" }} role="feed" aria-label="Job listings">
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", margin: "0 0 0.5rem" }}>
              Showing <strong>{filteredJobs.length}</strong> available positions
            </p>

            {filteredJobs.map((job) => {
              const isSelected = selectedJob && selectedJob.id === job.id;
              const cardMatch = calculateProfessionalMatch(job, candidateContext);
              const cardEval = evaluateAccessibilityCompatibility(
                candidatePrefs,
                job.accessibility_capabilities || []
              );
              const isApplied = candidateApplications.some(
                (a) => String(a.job_posting_id) === String(job.id)
              );

              return (
                <article
                  key={job.id}
                  onClick={() => handleSelectJob(job)}
                  tabIndex="0"
                  role="button"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleSelectJob(job);
                    }
                  }}
                  className="job-card"
                  style={{
                    background: isSelected ? "#f0f9ff" : "var(--color-surface, #ffffff)",
                    border: isSelected ? "2px solid var(--color-primary, #082048)" : "1px solid var(--color-border, #c5d7e8)",
                    borderRadius: "var(--radius-md, 0.75rem)",
                    padding: "1.25rem",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    boxShadow: isSelected ? "var(--shadow-md)" : "var(--shadow-sm)",
                  }}
                  aria-selected={isSelected}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                    <div>
                      <h2 style={{ fontSize: "1.125rem", fontWeight: "700", margin: "0 0 0.25rem", color: "var(--color-primary)" }}>
                        {job.title}
                      </h2>
                      <p style={{ fontWeight: "600", color: "var(--color-text-muted)", margin: "0 0 0.5rem", fontSize: "0.9375rem" }}>
                        {job.company_name || "Verified Inclusive Employer"}
                      </p>
                    </div>

                    {isApplied && (
                      <span className="status-badge status-active" style={{ fontSize: "0.75rem", whiteSpace: "nowrap" }}>
                        ✓ Applied
                      </span>
                    )}
                  </div>

                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", margin: "0.5rem 0", fontSize: "0.8125rem" }}>
                    {job.location && <span className="hero-pill">📍 {job.location}</span>}
                    {job.work_mode && <span className="hero-pill">💼 {job.work_mode}</span>}
                  </div>

                  {/* Professional Match Score Card Pill */}
                  {user && cardMatch.score !== null && (
                    <div style={{ marginTop: "0.75rem", padding: "0.5rem 0.75rem", background: "#e7f3fb", borderRadius: "var(--radius-sm)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "0.8125rem", fontWeight: "600", color: "var(--color-primary)" }}>
                        Professional Compatibility
                      </span>
                      <span style={{ fontWeight: "800", color: "var(--color-primary)", fontSize: "0.9375rem" }}>
                        {cardMatch.score}% &bull; {cardMatch.label}
                      </span>
                    </div>
                  )}

                  {/* Accessibility Summary */}
                  {candidatePrefs.length > 0 && (
                    <div style={{ marginTop: "0.5rem", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                      <span>Declared Needs: </span>
                      <strong style={{ color: "var(--color-success)" }}>
                        {cardEval.filter((e) => e.status === "AVAILABLE").length} Confirmed
                      </strong>
                      {cardEval.some((e) => e.isGap) && (
                        <span style={{ color: "var(--color-warning)", marginLeft: "0.5rem" }}>
                          &bull; {cardEval.filter((e) => e.isGap).length} Gaps / Needs Request
                        </span>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>

          {/* Right Column: Detailed Job View */}
          {selectedJob && (
            <div className="job-details-column" style={{
              background: "var(--color-surface, #ffffff)",
              border: "1px solid var(--color-border, #c5d7e8)",
              borderRadius: "var(--radius-lg, 1rem)",
              padding: "2rem",
              position: "sticky",
              top: "1rem",
              boxShadow: "var(--shadow-md)"
            }}>
              {/* Header */}
              <div style={{ borderBottom: "1px solid var(--color-border)", paddingBottom: "1.25rem", marginBottom: "1.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                  <div>
                    <p className="eyebrow" style={{ margin: "0 0 0.25rem" }}>JOB SPECIFICATION</p>
                    <h2 style={{ fontSize: "1.75rem", margin: "0 0 0.5rem", color: "var(--color-primary)" }}>
                      {selectedJob.title}
                    </h2>
                    <p style={{ fontSize: "1.125rem", fontWeight: "600", margin: "0 0 0.5rem" }}>
                      {selectedJob.company_name || "Verified Inclusive Employer"}
                    </p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", fontSize: "0.875rem" }}>
                      {selectedJob.location && <span>📍 {selectedJob.location}</span>}
                      {selectedJob.work_mode && <span>&bull; 💼 {selectedJob.work_mode}</span>}
                      <span>&bull; 📅 Posted {new Date(selectedJob.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {/* Apply Action CTA */}
                  <div style={{ textAlign: "right", minWidth: "160px" }}>
                    {alreadyApplied ? (
                      <button type="button" className="btn btn-secondary" disabled style={{ width: "100%" }}>
                        ✓ Already Applied
                      </button>
                    ) : user ? (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => setIsApplyModalOpen(true)}
                        style={{ width: "100%" }}
                      >
                        Apply Now
                      </button>
                    ) : (
                      <Link to="/login" className="btn btn-primary" style={{ width: "100%", display: "inline-block", textAlign: "center" }}>
                        Sign in to Apply
                      </Link>
                    )}
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => handleOpenAccommodationModal("")}
                      style={{ width: "100%", marginTop: "0.5rem", fontSize: "0.875rem" }}
                    >
                      Request Accommodation
                    </button>
                  </div>
                </div>
              </div>

              {/* 1. SEPARATE PROFESSIONAL MATCH SCORE SECTION */}
              <section className="professional-match-section" style={{
                background: "#f4f8fc",
                border: "1px solid #c5d7e8",
                borderRadius: "var(--radius-md)",
                padding: "1.25rem",
                marginBottom: "1.5rem"
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                  <h3 style={{ fontSize: "1.125rem", margin: 0, color: "var(--color-primary)" }}>
                    🎯 Professional Match Score
                  </h3>
                  {profMatch.score !== null ? (
                    <span style={{ fontSize: "1.25rem", fontWeight: "800", color: "var(--color-primary)" }}>
                      {profMatch.score}% ({profMatch.label})
                    </span>
                  ) : (
                    <span style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                      Guest mode (Sign in for personalized score)
                    </span>
                  )}
                </div>
                <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", margin: "0 0 0.5rem" }}>
                  Scored strictly on qualifications, experience, and role responsibilities. Accommodation needs are evaluated separately and <strong>never</strong> reduce your professional score.
                </p>
                {profMatch.highlights.length > 0 && (
                  <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
                    {profMatch.highlights.map((h) => (
                      <span key={h} className="hero-pill" style={{ background: "#ffffff", borderColor: "#7aa3c4", fontSize: "0.75rem" }}>
                        ✓ {h}
                      </span>
                    ))}
                  </div>
                )}
              </section>

              {/* 2. ACCESSIBILITY COMPATIBILITY & CAPABILITIES TABLE */}
              <section className="accessibility-evaluation-section" style={{ marginBottom: "1.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.75rem" }}>
                  <h3 style={{ fontSize: "1.125rem", margin: 0 }}>
                    ♿ Workplace Accessibility &amp; Accommodations
                  </h3>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => handleOpenAccommodationModal("")}
                    style={{ fontSize: "0.8125rem", color: "var(--color-secondary)" }}
                  >
                    + Request Custom Accommodation
                  </button>
                </div>

                {candidatePrefs.length > 0 ? (
                  <div className="table-responsive" style={{ border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                      <thead>
                        <tr style={{ background: "#e7f3fb", textAlign: "left", borderBottom: "1px solid var(--color-border)" }}>
                          <th style={{ padding: "0.75rem" }}>Your Declared Need</th>
                          <th style={{ padding: "0.75rem" }}>Employer Capability</th>
                          <th style={{ padding: "0.75rem" }}>Status</th>
                          <th style={{ padding: "0.75rem", textAlign: "right" }}>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {accessEval.map((item) => (
                          <tr key={item.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                            <td style={{ padding: "0.75rem", fontWeight: "600" }}>
                              {item.requirement}
                              {item.category && (
                                <span style={{ display: "block", fontSize: "0.75rem", fontWeight: "normal", color: "var(--color-text-muted)" }}>
                                  Category: {item.category}
                                </span>
                              )}
                            </td>
                            <td style={{ padding: "0.75rem" }}>
                              {item.employerDetails || item.display.description}
                            </td>
                            <td style={{ padding: "0.75rem", whiteSpace: "nowrap" }}>
                              <span
                                style={{
                                  display: "inline-block",
                                  padding: "0.2rem 0.5rem",
                                  borderRadius: "999px",
                                  fontSize: "0.75rem",
                                  fontWeight: "700",
                                  background:
                                    item.status === "AVAILABLE"
                                      ? "#d1e7dd"
                                      : item.status === "ON_REQUEST"
                                        ? "#cff4fc"
                                        : item.status === "NOT_SPECIFIED"
                                          ? "#fff3cd"
                                          : "#f8d7da",
                                  color:
                                    item.status === "AVAILABLE"
                                      ? "#0f5132"
                                      : item.status === "ON_REQUEST"
                                        ? "#055160"
                                        : item.status === "NOT_SPECIFIED"
                                          ? "#664d03"
                                          : "#842029",
                                }}
                              >
                                {item.display.icon} {item.display.label}
                              </span>
                            </td>
                            <td style={{ padding: "0.75rem", textAlign: "right" }}>
                              {item.canRequestAccommodation && (
                                <button
                                  type="button"
                                  className="btn btn-secondary btn-sm"
                                  style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
                                  onClick={() => handleOpenAccommodationModal(item.requirement)}
                                >
                                  Request
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ background: "#f8fafc", padding: "1rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}>
                    <p style={{ margin: "0 0 0.5rem", fontSize: "0.875rem" }}>
                      Employer publishes <strong>{selectedJob.accessibility_capabilities?.length || 0}</strong> confirmed accessibility capabilities.
                    </p>
                    {user ? (
                      <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                        Tip: <Link to="/candidate/dashboard">Declare your accessibility preferences</Link> to see personalized accommodation compatibility matching.
                      </p>
                    ) : (
                      <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                        <Link to="/login">Sign in</Link> to view side-by-side accommodation evaluation.
                      </p>
                    )}
                  </div>
                )}
              </section>

              {/* 3. JOB DESCRIPTION & RESPONSIBILITIES */}
              <section className="job-content-section" style={{ borderTop: "1px solid var(--color-border)", paddingTop: "1.5rem" }}>
                <h3 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>About the Role</h3>
                <div style={{ whiteSpace: "pre-line", lineHeight: "1.6", color: "var(--color-text)", fontSize: "0.9375rem", marginBottom: "1.5rem" }}>
                  {selectedJob.description}
                </div>

                {selectedJob.responsibilities && (
                  <div style={{ marginBottom: "1.5rem" }}>
                    <h4 style={{ fontSize: "1rem", fontWeight: "700", marginBottom: "0.5rem" }}>
                      Key Responsibilities
                    </h4>
                    <div style={{ whiteSpace: "pre-line", lineHeight: "1.6", fontSize: "0.9375rem" }}>
                      {selectedJob.responsibilities}
                    </div>
                  </div>
                )}

                {selectedJob.requirements && (
                  <div style={{ marginBottom: "1.5rem" }}>
                    <h4 style={{ fontSize: "1rem", fontWeight: "700", marginBottom: "0.5rem" }}>
                      Qualifications &amp; Requirements
                    </h4>
                    <div style={{ whiteSpace: "pre-line", lineHeight: "1.6", fontSize: "0.9375rem" }}>
                      {selectedJob.requirements}
                    </div>
                  </div>
                )}
              </section>
            </div>
          )}
        </div>
      )}

      {/* APPLICATION MODAL */}
      {isApplyModalOpen && selectedJob && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="apply-modal-title" style={{
          position: "fixed",
          inset: 0,
          background: "rgba(8, 32, 72, 0.6)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: "1rem",
          zIndex: 1000
        }}>
          <div className="modal-content" style={{
            background: "#ffffff",
            borderRadius: "var(--radius-lg, 1rem)",
            padding: "2rem",
            maxWidth: "550px",
            width: "100%",
            boxShadow: "var(--shadow-lg)"
          }}>
            <h2 id="apply-modal-title" style={{ marginTop: 0, color: "var(--color-primary)" }}>
              Apply for {selectedJob.title}
            </h2>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
              {selectedJob.company_name || "Verified Inclusive Employer"}
            </p>

            {appError && (
              <div className="form-error" role="alert" style={{ marginBottom: "1rem" }}>
                {appError}
              </div>
            )}

            <form onSubmit={handleSubmitApplication}>
              <div style={{ background: "#f0f9ff", padding: "1rem", borderRadius: "var(--radius-sm)", marginBottom: "1rem", fontSize: "0.875rem" }}>
                <p style={{ margin: "0 0 0.25rem", fontWeight: "600" }}>Applicant Profile</p>
                <p style={{ margin: 0 }}>Candidate: <strong>{user?.full_name || user?.email}</strong></p>
                <p style={{ margin: "0.25rem 0 0" }}>
                  Active Resume: {candidateResume ? <span>✓ {candidateResume.original_filename}</span> : <span style={{ color: "var(--color-warning)" }}>⚠️ No active resume uploaded (you can still apply)</span>}
                </p>
              </div>

              <div className="field-group" style={{ marginBottom: "1.25rem" }}>
                <label htmlFor="apply-cover-note" style={{ display: "block", fontWeight: "600", marginBottom: "0.4rem" }}>
                  Cover Note / Introduction (Optional)
                </label>
                <textarea
                  id="apply-cover-note"
                  rows="4"
                  maxLength={2000}
                  placeholder="Share a brief overview of your background, motivations, or special skills..."
                  value={coverNote}
                  onChange={(e) => setCoverNote(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}
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
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmittingApp}
                >
                  {isSubmittingApp ? "Submitting Application..." : "Confirm & Submit Application"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ACCOMMODATION REQUEST MODAL */}
      {isAccModalOpen && selectedJob && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="acc-modal-title" style={{
          position: "fixed",
          inset: 0,
          background: "rgba(8, 32, 72, 0.6)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: "1rem",
          zIndex: 1000
        }}>
          <div className="modal-content" style={{
            background: "#ffffff",
            borderRadius: "var(--radius-lg, 1rem)",
            padding: "2rem",
            maxWidth: "550px",
            width: "100%",
            boxShadow: "var(--shadow-lg)"
          }}>
            <h2 id="acc-modal-title" style={{ marginTop: 0, color: "var(--color-primary)" }}>
              Request Workplace Accommodation
            </h2>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
              For position: <strong>{selectedJob.title}</strong> at {selectedJob.company_name}
            </p>

            {accError && (
              <div className="form-error" role="alert" style={{ marginBottom: "1rem" }}>
                {accError}
              </div>
            )}

            <form onSubmit={handleSubmitAccommodation}>
              <div className="field-group" style={{ marginBottom: "1rem" }}>
                <label htmlFor="acc-facility-name" style={{ display: "block", fontWeight: "600", marginBottom: "0.4rem" }}>
                  Required Accommodation / Facility Name *
                </label>
                <input
                  id="acc-facility-name"
                  type="text"
                  required
                  placeholder="e.g. Screen reader test setup, ASL interpreter, Quiet room..."
                  value={accFacility}
                  onChange={(e) => setAccFacility(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}
                />
              </div>

              <div className="field-group" style={{ marginBottom: "1.25rem" }}>
                <label htmlFor="acc-description" style={{ display: "block", fontWeight: "600", marginBottom: "0.4rem" }}>
                  Additional Details &amp; Arrangement Preferences (Optional)
                </label>
                <textarea
                  id="acc-description"
                  rows="3"
                  maxLength={2000}
                  placeholder="Provide any technical or scheduling specifics. No medical documentation is required."
                  value={accDescription}
                  onChange={(e) => setAccDescription(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}
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
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmittingAcc}
                >
                  {isSubmittingAcc ? "Sending..." : "Submit Accommodation Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}

export default JobDiscoveryPage;

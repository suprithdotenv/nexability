import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { candidateService } from "../api/index.js";
import { useAuth } from "../context/useAuth.js";
import CandidateProfileEditor from "../components/CandidateProfileEditor.jsx";
import ResumeManager from "../components/ResumeManager.jsx";
import AccessibilityPreferencesManager from "../components/AccessibilityPreferencesManager.jsx";
import { MyApplications } from "../features/candidate/components/MyApplications.jsx";
import { MyAccommodations } from "../features/candidate/components/MyAccommodations.jsx";

function CandidateDashboardPage() {
  const { user, logout } = useAuth();
  const [hasDeclaration, setHasDeclaration] = useState(false);
  const [isLoadingDeclaration, setIsLoadingDeclaration] = useState(true);

  // Load declaration status
  useEffect(() => {
    let isMounted = true;
    async function loadDeclaration() {
      if (!candidateService.isDeclarationSupported) {
        if (isMounted) {
          setIsLoadingDeclaration(false);
          setHasDeclaration(false);
        }
        return;
      }

      try {
        const res = await candidateService.getDeclaration();
        if (isMounted && res && res.accepted) {
          setHasDeclaration(true);
        }
      } catch {
        // Declaration may not yet exist for this candidate – not an error
      } finally {
        if (isMounted) {
          setIsLoadingDeclaration(false);
        }
      }
    }

    loadDeclaration();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <main id="main-content" className="dashboard-main" tabIndex="-1">
      <div className="dashboard-container">
        {/* Header Section */}
        <header className="dashboard-header">
          <div className="dashboard-title-group">
            <p className="eyebrow">CANDIDATE PORTAL</p>
            <h1>Candidate Dashboard</h1>
            <p className="dashboard-greeting">
              Welcome back, <strong>{user?.full_name || user?.email || "Candidate"}</strong>.
            </p>
          </div>
          <div className="dashboard-actions">
            <Link className="btn btn-secondary" to="/candidate/settings">
              Settings &amp; Preferences
            </Link>
            <button className="btn btn-primary" type="button" onClick={logout}>
              Sign Out
            </button>
          </div>
        </header>

        {/* Dashboard Grid */}
        <div className="dashboard-grid">
          {/* Card 1: Account Profile & Editor */}
          <section className="dashboard-card" aria-labelledby="card-profile-title">
            <h2 id="card-profile-title" className="card-title">
              Account Profile
            </h2>
            <CandidateProfileEditor />
          </section>

          {/* Card 2: Resume Management */}
          <section className="dashboard-card" aria-labelledby="card-resume-title">
            <h2 id="card-resume-title" className="card-title">
              Resume &amp; Documents
            </h2>
            <p className="card-description">
              Upload your resume in PDF or DOCX format (maximum 5MB). You can download, replace,
              or delete your active document anytime.
            </p>
            <ResumeManager />
          </section>

          {/* Card 3: Accessibility Accommodations */}
          <section
            className="dashboard-card dashboard-card-wide"
            aria-labelledby="card-accommodations-title"
          >
            <h2 id="card-accommodations-title" className="card-title">
              Accessibility &amp; Workplace Accommodations
            </h2>
            <p className="card-description">
              Declare voluntary accommodations for interviews and work arrangements (screen readers,
              captions, flexible time, quiet workspace). No medical documentation is ever required.
            </p>
            <AccessibilityPreferencesManager />
          </section>

          {/* Card 4: Disability Self-Declaration */}
          <section className="dashboard-card" aria-labelledby="card-declaration-title">
            <div className="card-header-row">
              <h2 id="card-declaration-title" className="card-title">
                Disability Self-Declaration
              </h2>
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
                    ? "Pending Backend Support"
                    : hasDeclaration
                      ? "Active on File"
                      : "Not Declared"
                }`}
              >
                {isLoadingDeclaration
                  ? "Checking..."
                  : !candidateService.isDeclarationSupported
                    ? "Pending Backend Support"
                    : hasDeclaration
                      ? "Active on File"
                      : "Not Declared"}
              </span>
            </div>
            <p className="card-description">
              Your voluntary disability declaration is strictly optional and protected by privacy
              safeguards. No medical diagnosis paperwork is ever required.
            </p>
            <div className="card-footer-actions">
              <Link className="btn btn-secondary" to="/candidate/settings">
                View Declaration Status
              </Link>
            </div>
          </section>

          {/* Card 5: Career Opportunities */}
          <section className="dashboard-card" aria-labelledby="card-jobs-title">
            <h2 id="card-jobs-title" className="card-title">
              Inclusive Job Matches
            </h2>
            <p className="card-description">
              Discover opportunities with verified employers who prioritise accessible workplaces,
              universal design, and neurodivergent-friendly cultures.
            </p>
            <div className="card-footer-actions">
              <Link className="btn btn-primary" to="/jobs">
                Explore Open Positions
              </Link>
            </div>
          </section>

          {/* Card 6: My Job Applications */}
          <section
            className="dashboard-card dashboard-card-wide"
            aria-labelledby="card-applications-title"
          >
            <h2 id="card-applications-title" className="card-title" style={{ marginBottom: "1rem" }}>
              My Job Applications
            </h2>
            <MyApplications />
          </section>

          {/* Card 7: My Accommodation Requests */}
          <section
            className="dashboard-card dashboard-card-wide"
            aria-labelledby="card-my-accommodations-title"
          >
            <h2 id="card-my-accommodations-title" className="card-title" style={{ marginBottom: "1rem" }}>
              My Accommodation Requests
            </h2>
            <MyAccommodations />
          </section>
        </div>
      </div>
    </main>
  );
}

export default CandidateDashboardPage;

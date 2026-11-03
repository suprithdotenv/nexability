import { Link } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

function EmployerDashboardPage() {
  const { user, logout } = useAuth();
  const verificationStatus = (user?.verification_status || "PENDING").toUpperCase();

  const isVerified = verificationStatus === "VERIFIED";
  const isPending = verificationStatus === "PENDING";
  const isRejected = verificationStatus === "REJECTED";

  return (
    <main id="main-content" className="dashboard-main" tabIndex="-1">
      <div className="dashboard-container">
        {/* Header Section */}
        <header className="dashboard-header">
          <div className="dashboard-title-group">
            <p className="eyebrow">EMPLOYER RECRUITMENT PORTAL</p>
            <h1>{user?.company_name || "Employer Dashboard"}</h1>
            <p className="dashboard-greeting">
              Signed in as <strong>{user?.full_name || user?.email}</strong>.
            </p>
          </div>
          <div className="dashboard-actions">
            <button className="btn btn-primary" type="button" onClick={logout}>
              Sign Out
            </button>
          </div>
        </header>

        {/* Organization Verification Banner */}
        <section
          className={`verification-banner ${
            isVerified
              ? "verification-verified"
              : isRejected
                ? "verification-rejected"
                : "verification-pending"
          }`}
          role="status"
          aria-live="polite"
          aria-labelledby="verification-title"
        >
          <div className="verification-badge-row">
            <span
              className={`status-badge ${
                isVerified
                  ? "status-active"
                  : isRejected
                    ? "status-error"
                    : "status-warning"
              }`}
            >
              Status: {verificationStatus}
            </span>
          </div>
          <h2 id="verification-title" className="verification-heading">
            {isVerified && "Organization Verified & Approved"}
            {isPending && "Organization Verification Pending Approval"}
            {isRejected && "Organization Verification Requires Attention"}
          </h2>
          <p className="verification-text">
            {isVerified &&
              "Your organization is fully verified. You can publish accessible job postings, define accessibility capability benchmarks, and connect with candidate talent."}
            {isPending &&
              `Your corporate email domain (${user?.email_domain || "on file"}) is currently being reviewed by the NexAbility team. Standard recruitment features will unlock automatically upon approval.`}
            {isRejected &&
              "Your company verification could not be completed with the provided corporate credentials. Please contact our support team at support@nexability.org."}
          </p>
        </section>

        {/* Dashboard Grid */}
        <div className="dashboard-grid">
          {/* Card 1: Company Profile */}
          <section className="dashboard-card" aria-labelledby="card-company-profile">
            <h2 id="card-company-profile" className="card-title">
              Company Profile
            </h2>
            <div className="profile-details-list">
              <div className="profile-detail-item">
                <span className="detail-label">Company Name</span>
                <span className="detail-value">{user?.company_name || "Not provided"}</span>
              </div>
              <div className="profile-detail-item">
                <span className="detail-label">Corporate Domain</span>
                <span className="detail-value">{user?.email_domain || "Not provided"}</span>
              </div>
              <div className="profile-detail-item">
                <span className="detail-label">Recruiter Contact</span>
                <span className="detail-value">{user?.full_name || "Not provided"}</span>
              </div>
              <div className="profile-detail-item">
                <span className="detail-label">Account Email</span>
                <span className="detail-value">{user?.email}</span>
              </div>
              <div className="profile-detail-item">
                <span className="detail-label">Website</span>
                <span className="detail-value">{user?.website || "Not provided"}</span>
              </div>
            </div>
          </section>

          {/* Card 2: Workplace Accessibility Capabilities */}
          <section className="dashboard-card" aria-labelledby="card-accessibility-capabilities">
            <h2 id="card-accessibility-capabilities" className="card-title">
              Accessibility Capabilities
            </h2>
            <p className="card-description">
              Declare your organization&apos;s physical and digital accommodation capabilities to help
              candidates find roles where they thrive.
            </p>
            <ul className="dashboard-feature-list" aria-label="Available accessibility features">
              <li>Ergonomic workstations and assistive hardware</li>
              <li>Flexible sensory environments and quiet spaces</li>
              <li>Fully remote and hybrid schedule flexibility</li>
              <li>Screen-reader compatible digital toolsets</li>
            </ul>
          </section>

          {/* Card 3: Job Descriptions & Open Positions */}
          <section className="dashboard-card" aria-labelledby="card-job-documents">
            <h2 id="card-job-documents" className="card-title">
              Job Postings &amp; Documents
            </h2>
            <p className="card-description">
              Upload job descriptions for automated accessibility analysis and bias screening
              against universal hiring standards.
            </p>
            <div className="card-footer-actions">
              {isVerified ? (
                <button type="button" className="btn btn-primary" disabled>
                  Manage Job Documents
                </button>
              ) : (
                <p className="field-hint">
                  Job posting activates once organization verification status is VERIFIED.
                </p>
              )}
            </div>
          </section>

          {/* Card 4: Quick Navigation */}
          <section className="dashboard-card" aria-labelledby="card-help-support">
            <h2 id="card-help-support" className="card-title">
              Support &amp; Standards
            </h2>
            <p className="card-description">
              Learn more about WCAG 2.2 AA workplace standards, inclusive hiring guidelines, and
              corporate disability inclusion practices.
            </p>
            <div className="card-footer-actions">
              <Link className="btn btn-secondary" to="/">
                Explore Accessibility Guide
              </Link>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export default EmployerDashboardPage;


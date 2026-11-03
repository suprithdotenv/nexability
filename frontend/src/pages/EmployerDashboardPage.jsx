import { Link } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

function EmployerDashboardPage() {
  const { user, logout } = useAuth();

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
            <Link className="btn btn-secondary" to="/employer/portal">
              Open Full Portal
            </Link>
            <button className="btn btn-primary" type="button" onClick={logout}>
              Sign Out
            </button>
          </div>
        </header>

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
            <div className="card-footer-actions" style={{ marginTop: "1rem" }}>
              <Link className="btn btn-secondary" to="/employer/portal">
                Edit Company Profile
              </Link>
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
            <div className="card-footer-actions" style={{ marginTop: "1rem" }}>
              <Link className="btn btn-secondary" to="/employer/portal">
                Manage Accessibility Profile
              </Link>
            </div>
          </section>

          {/* Card 3: Job Descriptions & Open Positions */}
          <section className="dashboard-card" aria-labelledby="card-job-documents">
            <h2 id="card-job-documents" className="card-title">
              Job Postings &amp; Recruitment
            </h2>
            <p className="card-description">
              Publish accessible job listings with transparent accommodation parameters, track applicants, and manage recruitment.
            </p>
            <div className="card-footer-actions">
              <Link className="btn btn-primary" to="/employer/portal">
                Manage Job Postings
              </Link>
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

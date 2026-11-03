import { useState, useEffect } from "react";
import { useAuth } from "../../../context/useAuth.js";
import employerService from "../services/employerService.js";
import EmployerNavigation from "../components/EmployerNavigation.jsx";
import EmployerOverview from "../components/EmployerOverview.jsx";
import JobManager from "../components/JobManager.jsx";
import JobDocumentManager from "../components/JobDocumentManager.jsx";
import ApplicationsDashboard from "../components/ApplicationsDashboard.jsx";
import AccommodationInbox from "../components/AccommodationInbox.jsx";
import EmployerAccessibilityManager from "../components/EmployerAccessibilityManager.jsx";
import EmployerProfileEditor from "../components/EmployerProfileEditor.jsx";

function EmployerPortalPage() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [profile, setProfile] = useState(user || null);
  const [selectedJobForApps, setSelectedJobForApps] = useState(null);
  const [counts, setCounts] = useState({
    jobs: 0,
    applications: 0,
    accommodations: 0,
  });

  useEffect(() => {
    let ignore = false;
    async function fetchCounts() {
      try {
        const data = await employerService.getDashboard();
        if (!ignore) {
          if (data?.profile) setProfile(data.profile);
          if (data?.stats) {
            setCounts({
              jobs: data.stats.active_jobs || 0,
              applications: data.stats.pending_applications || 0,
              accommodations: data.stats.pending_accommodations || 0,
            });
          }
        }
      } catch {
        if (!ignore && user) {
          setProfile(user);
        }
      }
    }
    fetchCounts();
    return () => {
      ignore = true;
    };
  }, [user]);

  function handleSelectJobForApplications(jobId) {
    setSelectedJobForApps(jobId);
    setActiveTab("applications");
  }

  return (
    <main id="main-content" className="dashboard-main" tabIndex="-1">
      <div className="dashboard-container">
        {/* Header Section */}
        <header className="dashboard-header" style={{ marginBottom: "1.5rem" }}>
          <div className="dashboard-title-group">
            <p className="eyebrow">EMPLOYER RECRUITMENT &amp; ACCESSIBILITY PORTAL</p>
            <h1>{profile?.company_name || user?.company_name || "Employer Dashboard"}</h1>
            <p className="dashboard-greeting">
              Signed in as <strong>{profile?.full_name || user?.full_name || user?.email}</strong>.
            </p>
          </div>
          <div className="dashboard-actions">
            <button className="btn btn-primary" type="button" onClick={logout}>
              Sign Out
            </button>
          </div>
        </header>

        {/* Employer Portal Navigation Tabs */}
        <EmployerNavigation
          activeTab={activeTab}
          onSelectTab={(tab) => {
            if (tab !== "applications") setSelectedJobForApps(null);
            setActiveTab(tab);
          }}
          counts={counts}
        />

        {/* Active Tab View */}
        <div className="employer-tab-content">
          {activeTab === "overview" && (
            <EmployerOverview onNavigateTab={setActiveTab} />
          )}

          {activeTab === "jobs" && (
            <JobManager onSelectJobForApplications={handleSelectJobForApplications} />
          )}

          {activeTab === "documents" && (
            <JobDocumentManager />
          )}

          {activeTab === "applications" && (
            <ApplicationsDashboard selectedJobId={selectedJobForApps} />
          )}

          {activeTab === "accommodations" && (
            <AccommodationInbox />
          )}

          {activeTab === "accessibility" && (
            <EmployerAccessibilityManager />
          )}

          {activeTab === "profile" && (
            <EmployerProfileEditor
              profile={profile}
              onProfileUpdated={(updated) => setProfile(updated)}
            />
          )}
        </div>
      </div>
    </main>
  );
}

export default EmployerPortalPage;


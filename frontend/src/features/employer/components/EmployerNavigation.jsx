function EmployerNavigation({ activeTab, onSelectTab, counts = {} }) {
  const tabs = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "jobs", label: "Job Postings", icon: "💼", badge: counts.jobs },
    { id: "documents", label: "Job Documents", icon: "📁" },
    { id: "applications", label: "Applications", icon: "👥", badge: counts.applications },
    { id: "accommodations", label: "Accommodations", icon: "♿", badge: counts.accommodations },
    { id: "accessibility", label: "Accessibility Profile", icon: "🏛️" },
    { id: "profile", label: "Company Profile", icon: "🏢" },
  ];

  return (
    <nav className="employer-nav-tabs" aria-label="Employer portal sections" style={{
      display: "flex",
      gap: "0.5rem",
      flexWrap: "wrap",
      borderBottom: "1px solid var(--color-border, #e2e8f0)",
      marginBottom: "1.5rem",
      paddingBottom: "0.5rem"
    }}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            className={`btn ${isActive ? "btn-primary" : "btn-secondary"} btn-sm`}
            onClick={() => onSelectTab(tab.id)}
            aria-current={isActive ? "page" : undefined}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              borderRadius: "9999px",
              padding: "0.4rem 0.9rem",
              fontSize: "0.875rem",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            {tab.badge !== undefined && tab.badge > 0 && (
              <span
                style={{
                  background: isActive ? "#ffffff" : "var(--color-primary, #0284c7)",
                  color: isActive ? "var(--color-primary, #0284c7)" : "#ffffff",
                  fontSize: "0.75rem",
                  fontWeight: "bold",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "9999px",
                  marginLeft: "0.2rem",
                }}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
}

export default EmployerNavigation;


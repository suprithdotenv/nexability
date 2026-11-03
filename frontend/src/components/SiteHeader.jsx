import { useEffect, useId, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

function SiteHeader() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const navId = useId();
  const toggleRef = useRef(null);
  const navRef = useRef(null);

  // Sync state during render when location changes, avoiding effect cascading renders
  const locationKey = location.pathname + location.hash + location.search;
  const [prevLocationKey, setPrevLocationKey] = useState(locationKey);
  if (prevLocationKey !== locationKey) {
    setPrevLocationKey(locationKey);
    setMenuOpen(false);
  }

  const closeMenu = () => setMenuOpen(false);

  async function handleLogout() {
    closeMenu();
    await logout();
    navigate("/", { replace: true });
  }

  const userRole = (user?.role || "").toLowerCase();
  const dashboardPath =
    userRole === "employer" ? "/employer/dashboard" : "/candidate/dashboard";

  useEffect(() => {
    if (!menuOpen) {
      return undefined;
    }

    const nav = navRef.current;
    const firstLink = nav?.querySelector("a, button");
    firstLink?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        toggleRef.current?.focus();
        return;
      }

      if (event.key !== "Tab" || !nav) {
        return;
      }

      const isMobile = window.matchMedia("(max-width: 1024px)").matches;
      if (!isMobile) {
        return;
      }

      const focusable = [
        ...nav.querySelectorAll("a[href], button:not([disabled])"),
      ];
      if (focusable.length === 0) {
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    document.body.classList.add("nav-open");

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.classList.remove("nav-open");
    };
  }, [menuOpen]);

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Link className="brand" to="/" onClick={closeMenu} aria-label="NexAbility Home">
          <img
            className="brand-logo"
            src="/assets/nexability-logo.png"
            alt="NexAbility"
            width="220"
            height="110"
          />
        </Link>

        <button
          ref={toggleRef}
          type="button"
          className="nav-toggle"
          aria-expanded={menuOpen}
          aria-controls={navId}
          aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="nav-toggle-icon" aria-hidden="true">
            {menuOpen ? "✕" : "☰"}
          </span>
          <span className="nav-toggle-text">{menuOpen ? "Close" : "Menu"}</span>
        </button>

        <nav
          ref={navRef}
          id={navId}
          className={menuOpen ? "site-nav is-open" : "site-nav"}
          aria-label="Primary"
        >
          <div className="site-nav-links">
            {user ? (
              <>
                <Link to={dashboardPath} onClick={closeMenu}>
                  Dashboard
                </Link>
                {userRole === "candidate" && (
                  <Link to="/candidate/settings" onClick={closeMenu}>
                    Settings
                  </Link>
                )}
                <a href="/#about" onClick={closeMenu}>
                  About
                </a>
                <a href="/#accessibility" onClick={closeMenu}>
                  Accessibility
                </a>
              </>
            ) : (
              <>
                <Link to="/register?role=candidate" onClick={closeMenu}>
                  For Candidates
                </Link>
                <Link to="/register?role=employer" onClick={closeMenu}>
                  For Employers
                </Link>
                <a href="/#about" onClick={closeMenu}>
                  About
                </a>
                <a href="/#accessibility" onClick={closeMenu}>
                  Accessibility
                </a>
              </>
            )}
          </div>

          <div className="header-actions">
            {user ? (
              <>
                <Link
                  className="btn btn-secondary header-btn"
                  to={dashboardPath}
                  onClick={closeMenu}
                >
                  {userRole === "employer" ? "Employer Portal" : "My Dashboard"}
                </Link>
                <button
                  className="btn btn-primary header-btn"
                  type="button"
                  onClick={handleLogout}
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link className="btn btn-secondary header-btn" to="/login" onClick={closeMenu}>
                  Sign In
                </Link>
                <Link className="btn btn-primary header-btn" to="/register" onClick={closeMenu}>
                  Get Started
                </Link>
              </>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}

export default SiteHeader;

import { Link } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

function HomePage() {
  const { user } = useAuth();
  const userRole = (user?.role || "").toLowerCase();
  const dashboardPath =
    userRole === "employer" ? "/employer/dashboard" : "/candidate/dashboard";

  return (
    <main id="main-content" tabIndex="-1">
      {/* 1. HERO SECTION */}
      <section className="hero" id="home" aria-labelledby="hero-title">
        <div className="hero-copy">
          <p className="eyebrow">ACCESSIBLE EMPLOYMENT FOR EVERYONE</p>
          <h1 id="hero-title">Your ability deserves to be seen.</h1>
          <p className="hero-description">
            Discover opportunities, showcase your strengths, and connect with employers who value inclusive talent.
          </p>
          <div className="hero-actions">
            {user ? (
              <>
                <Link className="btn btn-primary" to={dashboardPath}>
                  Go to {userRole === "employer" ? "Employer Portal" : "My Dashboard"}
                </Link>
                {userRole === "candidate" && (
                  <Link className="btn btn-secondary" to="/candidate/settings">
                    Settings
                  </Link>
                )}
              </>
            ) : (
              <>
                <Link className="btn btn-primary" to="/register?role=candidate">
                  Find Opportunities
                </Link>
                <Link className="btn btn-secondary" to="/register?role=employer">
                  Hire Inclusively
                </Link>
              </>
            )}
          </div>
          <div className="hero-highlights" aria-label="Key platform qualities">
            <span className="hero-pill">✓ Accessible Profiles</span>
            <span className="hero-pill">✓ Inclusive Employers</span>
            <span className="hero-pill">✓ Barrier-Free Matching</span>
          </div>
        </div>

        <div className="hero-visual" aria-hidden="true">
          <div className="visual-panel">
            <div className="visual-orbit orbit-one" />
            <div className="visual-orbit orbit-two" />

            <div className="visual-card candidate-badge-card">
              <div className="visual-badge-header">
                <span className="visual-avatar">JD</span>
                <div>
                  <span className="visual-name">Candidate Profile</span>
                  <span className="visual-role">Software Engineer</span>
                </div>
              </div>
              <div className="visual-tags">
                <span className="visual-tag">Screen-Reader Ready</span>
                <span className="visual-tag">Remote Work</span>
              </div>
              <span className="visual-status">✓ Skills Verified</span>
            </div>

            <div className="visual-card employer-badge-card">
              <div className="visual-badge-header">
                <span className="visual-avatar avatar-navy">AC</span>
                <div>
                  <span className="visual-name">Inclusive Employer</span>
                  <span className="visual-role">Hiring Active</span>
                </div>
              </div>
              <span className="visual-match">Matched on Ability</span>
              <span className="visual-status status-cyan">★ Equal Opportunity</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. VALUE PROPOSITIONS */}
      <section className="content-section" id="about" tabIndex="-1" aria-labelledby="why-title">
        <div className="section-header">
          <p className="eyebrow">BUILT FOR INCLUSION</p>
          <h2 id="why-title">Why NexAbility is different.</h2>
          <p className="section-intro">
            Traditional hiring platforms create unintended barriers. We designed NexAbility from
            the ground up to be accessible, equitable, and dignified.
          </p>
        </div>

        <div className="feature-grid">
          <article className="feature-card">
            <span className="feature-icon" aria-hidden="true">
              ♿
            </span>
            <h3>Accessibility by Default</h3>
            <p>
              Full keyboard navigability, high-contrast typography, screen-reader compatibility,
              and customizable viewing settings built into every screen.
            </p>
          </article>

          <article className="feature-card">
            <span className="feature-icon" aria-hidden="true">
              🛡️
            </span>
            <h3>Voluntary &amp; Private</h3>
            <p>
              Candidates decide what to share, when to share it, and with whom. Self-declaration is
              always optional and completely independent of job applications.
            </p>
          </article>

          <article className="feature-card">
            <span className="feature-icon" aria-hidden="true">
              🤝
            </span>
            <h3>Verified Inclusive Employers</h3>
            <p>
              Every employer on NexAbility agrees to our accessibility pledge and commits to
              workplace accommodations and barrier-free interview processes.
            </p>
          </article>

          <article className="feature-card">
            <span className="feature-icon" aria-hidden="true">
              ✨
            </span>
            <h3>Skill-First Matching</h3>
            <p>
              Focus on capabilities, problem-solving, and potential. We remove the cognitive biases
              and artificial barriers of traditional applicant tracking systems.
            </p>
          </article>
        </div>
      </section>

      {/* 4. DUAL AUDIENCE SPLIT */}
      <section className="content-section surface-muted" aria-labelledby="paths-title">
        <div className="section-header">
          <p className="eyebrow">YOUR PATHWAY</p>
          <h2 id="paths-title">Built for both sides of the table.</h2>
          <p className="section-intro">
            Whether you are looking for your next opportunity or seeking to build a more diverse,
            innovative team, NexAbility is your platform.
          </p>
        </div>

        <div className="dual-grid">
          <article className="audience-card audience-candidate">
            <span className="audience-badge">FOR JOB SEEKERS</span>
            <h3>Find work where your abilities are valued.</h3>
            <p>
              Create an accessible profile, showcase your unique talents, and connect with
              employers who understand the value of universal design and workplace flexibility.
            </p>
            <ul className="audience-benefits">
              <li>✓ Free forever for all job seekers</li>
              <li>✓ Screen-reader optimized application workflows</li>
              <li>✓ Direct access to inclusive hiring teams</li>
              <li>✓ No medical documentation or proof required</li>
            </ul>
            <div className="audience-action">
              <Link className="btn btn-primary" to="/register?role=candidate">
                Create Candidate Account
              </Link>
            </div>
          </article>

          <article className="audience-card audience-employer">
            <span className="audience-badge badge-accent">FOR EMPLOYERS</span>
            <h3>Access a broader pool of exceptional talent.</h3>
            <p>
              Connect with skilled professionals with disabilities, neurodivergent thinkers, and
              diverse problem solvers who bring transformative value to your organization.
            </p>
            <ul className="audience-benefits">
              <li>✓ Corporate email domain verification</li>
              <li>✓ Accessibility-screened job postings</li>
              <li>✓ Inclusion guidance and accommodation templates</li>
              <li>✓ Meaningful reporting on inclusive talent reach</li>
            </ul>
            <div className="audience-action">
              <Link className="btn btn-accent" to="/register?role=employer">
                Hire Inclusively
              </Link>
            </div>
          </article>
        </div>
      </section>

      {/* 5. ACCESSIBILITY SECTION */}
      <section
        className="content-section accessibility-section"
        id="accessibility"
        tabIndex="-1"
        aria-labelledby="accessibility-title"
      >
        <div className="section-header">
          <p className="eyebrow">ACCESSIBILITY</p>
          <h2 id="accessibility-title">Built to be used by everyone.</h2>
          <p className="section-intro">
            Keyboard access, clear language, and screen-reader support are part
            of every NexAbility flow.
          </p>
        </div>

        <div className="accessibility-grid">
          <div className="accessibility-card">
            <h3>Full Keyboard Navigation</h3>
            <p>
              Navigate the entire platform using logical tab order, skip links,
              and high-contrast focus indicators on every control.
            </p>
          </div>
          <div className="accessibility-card">
            <h3>Assistive Tech Compatible</h3>
            <p>
              Built with semantic HTML landmarks, live ARIA regions, and clear
              descriptive labels for screen-reader users.
            </p>
          </div>
          <div className="accessibility-card">
            <h3>WCAG 2.2 AA Contrast</h3>
            <p>
              Every text element and control meets or exceeds standard color contrast
              ratios with support for system reduced-motion preferences.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

export default HomePage;

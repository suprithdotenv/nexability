import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { authService } from "../api/index.js";
import DisabilityDeclaration from "../components/DisabilityDeclaration.jsx";

function RegisterPage() {
  const [searchParams] = useSearchParams();
  const requestedRole = searchParams.get("role");
  const validRole =
    requestedRole === "employer" || requestedRole === "candidate"
      ? requestedRole
      : "";

  const [role, setRole] = useState(validRole);
  const [prevRoleParam, setPrevRoleParam] = useState(requestedRole);

  // Registration step: 1 = Email & OTP Request, 2 = Verify OTP, 3 = Profile Details, 4 = Success
  const [step, setStep] = useState(1);

  // Form fields
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [verificationTicket, setVerificationTicket] = useState("");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [phone, setPhone] = useState("");
  const [website, setWebsite] = useState("");
  const [password, setPassword] = useState("");

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [registeredUser, setRegisteredUser] = useState(null);
  const [declarationResult, setDeclarationResult] = useState(null);

  function handleDeclarationComplete(result) {
    setDeclarationResult(result);
    try {
      localStorage.setItem("candidate_onboarding_declaration_completed", "true");
    } catch {
      // Ignore storage limitations
    }
    setStep(5);
  }

  if (prevRoleParam !== requestedRole) {
    setPrevRoleParam(requestedRole);
    if (requestedRole === "employer" || requestedRole === "candidate") {
      setRole(requestedRole);
    }
  }

  const otpPurpose =
    role === "employer" ? "EMPLOYER_REGISTRATION" : "CANDIDATE_REGISTRATION";

  // Step 1: Send OTP (with employer email screening if role is employer)
  async function handleSendOtp(event) {
    event.preventDefault();
    setError("");
    setStatusMessage("");

    if (!role) {
      setError("Please select whether you are a Candidate or an Employer.");
      return;
    }

    if (!email.trim()) {
      setError("Please enter your email address.");
      return;
    }

    setIsLoading(true);
    try {
      if (role === "employer") {
        const check = await authService.checkEmployerEmail(email.trim());
        if (!check.eligible) {
          setError(
            check.reason ||
              "Please use your official company email address to register as an employer."
          );
          setIsLoading(false);
          return;
        }
      }

      const res = await authService.sendOtp(email.trim(), otpPurpose);

      // Conforms to live OpenAPI schema: { message: string, expires_in: number | null }
      // Do not invent challenge_id or response fields
      const message = res?.message || "Verification code sent to your email.";
      const statusText = res?.expires_in
        ? `${message} (Code expires in ${res.expires_in} seconds)`
        : message;

      setStatusMessage(statusText);
      setStep(2);
    } catch (err) {
      const status = err.status || null;
      if (err.isProxyError || status === 502 || status === 504) {
        setError(
          err.message ||
            "Proxy error: Unable to connect to backend server. Please verify proxy target is active."
        );
      } else if (err.isNetworkError || status === 0) {
        setError(
          err.message ||
            "Network error: Unable to connect to server. Please check your internet connection."
        );
      } else if (status === 404) {
        setError(
          err.message ||
            "Not Found (404): The requested authentication endpoint could not be found."
        );
      } else if (status === 422) {
        setError(
          err.message ||
            "Validation Error (422): Invalid request data. Please check your email and input."
        );
      } else if (status === 429) {
        setError(
          err.message ||
            "Rate Limited (429): Too many requests. Please wait a moment before trying again."
        );
      } else {
        setError(
          err.message ||
            "Failed to send verification code. Please try again."
        );
      }
    } finally {
      setIsLoading(false);
    }
  }

  // Step 2: Verify OTP
  async function handleVerifyOtp(event) {
    event.preventDefault();
    setError("");
    setStatusMessage("");

    if (!otp.trim()) {
      setError("Please enter the verification code sent to your email.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.verifyOtp(email.trim(), otpPurpose, otp.trim());
      if (res.verified && res.verification_ticket) {
        setVerificationTicket(res.verification_ticket);
        setStatusMessage(res.message || "Email verified successfully. Please complete your profile.");
        setStep(3);
      } else {
        setError(res.message || "Verification failed. Please check the code and try again.");
      }
    } catch (err) {
      const status = err.status || null;
      if (err.isProxyError || status === 502 || status === 504) {
        setError(
          err.message ||
            "Proxy error: Unable to connect to backend server. Please verify proxy target is active."
        );
      } else if (err.isNetworkError || status === 0) {
        setError(
          err.message ||
            "Network error: Unable to connect to server. Please check your internet connection."
        );
      } else if (status === 404) {
        setError(
          err.message ||
            "Not Found (404): The verification endpoint could not be found."
        );
      } else if (status === 422) {
        setError(
          err.message ||
            "Validation Error (422): Invalid verification data. Please check the code."
        );
      } else if (status === 429) {
        setError(
          err.message ||
            "Rate Limited (429): Too many attempts. Please wait a moment before trying again."
        );
      } else {
        setError(
          err.message ||
            "Invalid verification code. Please try again."
        );
      }
    } finally {
      setIsLoading(false);
    }
  }

  // Step 3: Complete registration
  async function handleCompleteRegistration(event) {
    event.preventDefault();
    setError("");
    setStatusMessage("");

    if (!fullName.trim()) {
      setError("Full name is required.");
      return;
    }

    if (role === "employer" && !companyName.trim()) {
      setError("Company name is required for employer registration.");
      return;
    }

    if (!password || password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (!verificationTicket) {
      setError("Verification ticket expired or missing. Please restart verification.");
      setStep(1);
      return;
    }

    setIsLoading(true);
    try {
      let result;
      if (role === "candidate") {
        result = await authService.registerCandidate({
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          phone: phone.trim() || null,
          verification_ticket: verificationTicket,
        });
      } else {
        result = await authService.registerEmployer({
          full_name: fullName.trim(),
          company_name: companyName.trim(),
          email: email.trim(),
          password,
          phone: phone.trim() || null,
          website: website.trim() || null,
          verification_ticket: verificationTicket,
        });
      }

      setRegisteredUser(result);
      if (role === "candidate") {
        setStep(4);
      } else {
        setStep(5);
      }
    } catch (err) {
      const status = err.status || null;
      if (err.isProxyError || status === 502 || status === 504) {
        setError(
          err.message ||
            "Proxy error: Unable to connect to backend server. Please verify proxy target is active."
        );
      } else if (err.isNetworkError || status === 0) {
        setError(
          err.message ||
            "Network error: Unable to connect to server. Please check your internet connection."
        );
      } else if (status === 404) {
        setError(
          err.message ||
            "Not Found (404): Registration endpoint could not be found."
        );
      } else if (status === 422) {
        setError(
          err.message ||
            "Validation Error (422): Please check your registration details."
        );
      } else if (status === 429) {
        setError(
          err.message ||
            "Rate Limited (429): Too many registration attempts. Please try again later."
        );
      } else {
        setError(
          err.message ||
            "Registration failed. Please check the provided information."
        );
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main id="main-content" className="auth-main" tabIndex="-1">
      <section className="auth-panel" aria-labelledby="register-title">
        <p className="eyebrow">Get started</p>
        <h1 id="register-title">Create your NexAbility account</h1>
        <p>Join as a candidate or as an employer.</p>

        {/* Step indicator */}
        <div className="auth-steps" aria-label="Registration progress">
          <span className={step >= 1 ? "auth-step is-active" : "auth-step"}>
            1. Account & Email
          </span>
          <span className={step >= 2 ? "auth-step is-active" : "auth-step"}>
            2. Verify OTP
          </span>
          <span className={step >= 3 ? "auth-step is-active" : "auth-step"}>
            3. {role === "employer" ? "Company Details" : "Profile Details"}
          </span>
          {role === "candidate" && (
            <span className={step >= 4 ? "auth-step is-active" : "auth-step"}>
              4. Optional Onboarding
            </span>
          )}
        </div>

        {/* STEP 1: Role Selection & Email */}
        {step === 1 && (
          <form className="auth-form" onSubmit={handleSendOtp} noValidate>
            <fieldset
              className="role-fieldset"
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "role-error" : undefined}
            >
              <legend>Account type</legend>
              <div className="role-grid">
                <label
                  className={
                    role === "candidate" ? "role-option is-selected" : "role-option"
                  }
                >
                  <input
                    type="radio"
                    name="account-type"
                    value="candidate"
                    checked={role === "candidate"}
                    onChange={() => {
                      setRole("candidate");
                      setError("");
                    }}
                  />
                  <span>
                    <strong>Candidate</strong>
                    Find accessible career opportunities.
                  </span>
                </label>

                <label
                  className={
                    role === "employer" ? "role-option is-selected" : "role-option"
                  }
                >
                  <input
                    type="radio"
                    name="account-type"
                    value="employer"
                    checked={role === "employer"}
                    onChange={() => {
                      setRole("employer");
                      setError("");
                    }}
                  />
                  <span>
                    <strong>Employer</strong>
                    Discover inclusive talent.
                  </span>
                </label>
              </div>
            </fieldset>

            <div>
              <label className="field-label" htmlFor="register-email">
                {role === "employer" ? "Corporate email address" : "Email address"}
              </label>
              <input
                className="field-control"
                id="register-email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder={
                  role === "employer" ? "recruiter@company.com" : "you@example.com"
                }
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
              {role === "employer" && (
                <small className="field-hint">
                  Must be your corporate email domain (public domains like gmail/yahoo are excluded).
                </small>
              )}
            </div>

            <button className="btn btn-primary" type="submit" disabled={isLoading}>
              {isLoading ? "Sending Code..." : "Send Verification Code"}
            </button>
          </form>
        )}

        {/* STEP 2: Verify OTP */}
        {step === 2 && (
          <form className="auth-form" onSubmit={handleVerifyOtp} noValidate>
            <p className="step-description">
              We sent a one-time verification code to <strong>{email}</strong>.
            </p>

            <div>
              <label className="field-label" htmlFor="register-otp">
                Enter 6-digit verification code
              </label>
              <input
                className="field-control"
                id="register-otp"
                name="otp"
                type="text"
                autoComplete="one-time-code"
                placeholder="123456"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <div className="auth-button-group">
              <button className="btn btn-primary" type="submit" disabled={isLoading}>
                {isLoading ? "Verifying..." : "Verify Code"}
              </button>
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => setStep(1)}
                disabled={isLoading}
              >
                Change Email
              </button>
            </div>
          </form>
        )}

        {/* STEP 3: Complete Profile */}
        {step === 3 && (
          <form className="auth-form" onSubmit={handleCompleteRegistration} noValidate>
            <div>
              <label className="field-label" htmlFor="register-name">
                Full name
              </label>
              <input
                className="field-control"
                id="register-name"
                name="fullName"
                type="text"
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            {role === "employer" && (
              <div>
                <label className="field-label" htmlFor="register-company">
                  Company name
                </label>
                <input
                  className="field-control"
                  id="register-company"
                  name="companyName"
                  type="text"
                  autoComplete="organization"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>
            )}

            <div>
              <label className="field-label" htmlFor="register-phone">
                Phone number (optional)
              </label>
              <input
                className="field-control"
                id="register-phone"
                name="phone"
                type="tel"
                autoComplete="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                disabled={isLoading}
              />
            </div>

            {role === "employer" && (
              <div>
                <label className="field-label" htmlFor="register-website">
                  Company website (optional)
                </label>
                <input
                  className="field-control"
                  id="register-website"
                  name="website"
                  type="url"
                  placeholder="https://company.com"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            )}

            <div>
              <label className="field-label" htmlFor="register-password">
                Password (min. 8 characters)
              </label>
              <input
                className="field-control"
                id="register-password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <div className="auth-button-group">
              <button className="btn btn-primary" type="submit" disabled={isLoading}>
                {isLoading ? "Creating Account..." : "Complete Registration"}
              </button>
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => { setError(""); setStatusMessage(""); setStep(2); }}
                disabled={isLoading}
              >
                &larr; Back
              </button>
            </div>
          </form>
        )}

        {/* STEP 4: Candidate Onboarding - Optional Disability Declaration */}
        {step === 4 && role === "candidate" && (
          <DisabilityDeclaration
            onComplete={handleDeclarationComplete}
            onBack={() => { setError(""); setStatusMessage(""); setStep(3); }}
          />
        )}

        {/* STEP 5: Registration Success */}
        {step === 5 && (
          <div className="auth-success-panel" role="status">
            <h2>Account Created Successfully!</h2>
            <p>
              Welcome, <strong>{registeredUser?.full_name || fullName}</strong>! Your
              account has been registered as <em>{role}</em>.
            </p>
            {registeredUser?.verification_status && (
              <p>Status: {registeredUser.verification_status}</p>
            )}

            {role === "candidate" && (
              <div className="candidate-onboarding-summary">
                {declarationResult?.declared ? (
                  <p className="declaration-confirmed-badge">
                    &#10003; Voluntary disability self-declaration preference noted {declarationResult?.backendPending ? "(Awaiting backend storage deployment)" : "and recorded"}.
                  </p>
                ) : (
                  <p className="declaration-skipped-badge">
                    Disability self-declaration was not submitted. It remains completely optional.
                  </p>
                )}
                <p className="declaration-summary-note">
                  You can review, submit, or withdraw your declaration anytime in Candidate Settings.
                </p>
              </div>
            )}

            <div className="auth-actions">
              <Link className="btn btn-primary" to="/login">
                Proceed to Sign In
              </Link>
              {role === "candidate" && (
                <Link className="btn btn-secondary" to="/candidate/settings">
                  Candidate Settings
                </Link>
              )}
            </div>
          </div>
        )}

        {error ? (
          <p className="form-error" id="role-error" role="alert">
            {error}
          </p>
        ) : null}

        {statusMessage ? (
          <p className="form-status" role="status">
            {statusMessage}
          </p>
        ) : null}

        {step !== 4 && step !== 5 && (
          <p>
            Already have an account? <Link to="/login">Sign In</Link>
          </p>
        )}
      </section>
    </main>
  );
}

export default RegisterPage;

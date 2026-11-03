import { useState } from "react";
import { Link } from "react-router-dom";
import { authService } from "../api/index.js";

function ForgotPasswordPage() {
  const [step, setStep] = useState(1); // 1: Email, 2: OTP, 3: New Password, 4: Success
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [verificationTicket, setVerificationTicket] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  // Step 1: Request Password Reset OTP
  async function handleSendOtp(e) {
    e.preventDefault();
    setError("");
    setStatusMessage("");

    if (!email.trim()) {
      setError("Please enter your registered account email.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.forgotPassword(email.trim());
      setStatusMessage(res?.message || "Password reset OTP sent to your email.");
      setStep(2);
    } catch (err) {
      setError(err.message || "Failed to request password reset. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  // Step 2: Verify OTP
  async function handleVerifyOtp(e) {
    e.preventDefault();
    setError("");
    setStatusMessage("");

    if (!otp.trim()) {
      setError("Please enter the verification code sent to your email.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.verifyOtp(email.trim(), "PASSWORD_RESET", otp.trim());
      if (res?.verification_ticket) {
        setVerificationTicket(res.verification_ticket);
        setStatusMessage("Code verified. Please set your new password.");
        setStep(3);
      } else {
        setError("Invalid or expired verification code.");
      }
    } catch (err) {
      setError(err.message || "Verification code check failed.");
    } finally {
      setIsLoading(false);
    }
  }

  // Step 3: Reset Password
  async function handleResetPassword(e) {
    e.preventDefault();
    setError("");
    setStatusMessage("");

    if (!newPassword || newPassword.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      await authService.resetPassword({
        email: email.trim(),
        verification_ticket: verificationTicket,
        new_password: newPassword,
      });
      setStatusMessage("Your password has been reset successfully.");
      setStep(4);
    } catch (err) {
      setError(err.message || "Failed to reset password. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main id="main-content" className="auth-main" tabIndex="-1">
      <section className="auth-panel" aria-labelledby="reset-title">
        <p className="eyebrow">Account Recovery</p>
        <h1 id="reset-title">Reset your password.</h1>

        {error && (
          <div className="form-error" role="alert" aria-live="assertive">
            {error}
          </div>
        )}

        {statusMessage && (
          <div className="form-status" role="status" aria-live="polite">
            {statusMessage}
          </div>
        )}

        {step === 1 && (
          <form className="auth-form" onSubmit={handleSendOtp} noValidate>
            <p>Enter your email address to receive a password reset verification code.</p>
            <div className="field-group">
              <label htmlFor="reset-email">Account Email</label>
              <input
                id="reset-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                required
                autoComplete="email"
                disabled={isLoading}
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={isLoading}>
              {isLoading ? "Sending Code..." : "Send Reset Code"}
            </button>
            <div className="auth-links" style={{ marginTop: "1.5rem" }}>
              <Link to="/login">Back to Sign In</Link>
            </div>
          </form>
        )}

        {step === 2 && (
          <form className="auth-form" onSubmit={handleVerifyOtp} noValidate>
            <p>
              We sent a verification code to <strong>{email}</strong>. Please enter the 6-digit code.
            </p>
            <div className="field-group">
              <label htmlFor="reset-otp">Verification Code (OTP)</label>
              <input
                id="reset-otp"
                type="text"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                placeholder="123456"
                required
                autoComplete="one-time-code"
                disabled={isLoading}
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={isLoading}>
              {isLoading ? "Verifying..." : "Verify Code"}
            </button>
            <div className="auth-links" style={{ marginTop: "1rem" }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setStep(1)}
                disabled={isLoading}
              >
                Change Email
              </button>
            </div>
          </form>
        )}

        {step === 3 && (
          <form className="auth-form" onSubmit={handleResetPassword} noValidate>
            <p>Create a strong password with at least 8 characters.</p>
            <div className="field-group">
              <label htmlFor="new-password">New Password</label>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 8 characters"
                required
                minLength={8}
                autoComplete="new-password"
                disabled={isLoading}
              />
            </div>
            <div className="field-group">
              <label htmlFor="confirm-new-password">Confirm New Password</label>
              <input
                id="confirm-new-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                required
                minLength={8}
                autoComplete="new-password"
                disabled={isLoading}
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={isLoading}>
              {isLoading ? "Resetting Password..." : "Set New Password"}
            </button>
          </form>
        )}

        {step === 4 && (
          <div className="auth-authenticated" role="status">
            <p style={{ color: "var(--color-success, #00875a)", fontWeight: "600" }}>
              ✓ Your password has been successfully updated!
            </p>
            <p>You can now sign in with your new credentials.</p>
            <div className="auth-actions" style={{ marginTop: "1.5rem" }}>
              <Link className="btn btn-primary" to="/login">
                Proceed to Sign In
              </Link>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}

export default ForgotPasswordPage;

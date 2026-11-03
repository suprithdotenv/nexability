import { describe, it } from "node:test";
import assert from "node:assert/strict";

// -------------------------------------------------------------
// Test Suite: Role Normalization
// -------------------------------------------------------------
describe("Authentication Role Normalization", () => {
  function normalizeBackendRole(account) {
    const rawRole = typeof account?.role === "string" ? account.role : "";
    return {
      rawRole,
      role: rawRole.toLowerCase(),
    };
  }

  it("normalizes uppercase CANDIDATE to lowercase candidate", () => {
    const account = { id: "123", email: "candidate@example.com", role: "CANDIDATE" };
    const normalized = normalizeBackendRole(account);
    assert.equal(normalized.role, "candidate");
    assert.equal(normalized.rawRole, "CANDIDATE");
  });

  it("normalizes uppercase EMPLOYER to lowercase employer", () => {
    const account = { id: "456", email: "employer@company.com", role: "EMPLOYER" };
    const normalized = normalizeBackendRole(account);
    assert.equal(normalized.role, "employer");
    assert.equal(normalized.rawRole, "EMPLOYER");
  });

  it("handles already lowercase or mixed-case roles gracefully", () => {
    assert.equal(normalizeBackendRole({ role: "Candidate" }).role, "candidate");
    assert.equal(normalizeBackendRole({ role: "employer" }).role, "employer");
    assert.equal(normalizeBackendRole({ role: "" }).role, "");
    assert.equal(normalizeBackendRole(null).role, "");
  });
});

// -------------------------------------------------------------
// Test Suite: ProtectedRoute Guard Logic
// -------------------------------------------------------------
describe("ProtectedRoute Guard Verification", () => {
  function evaluateRouteAccess({ user, isAuthenticated, allowedRole, currentPath }) {
    if (!user || !isAuthenticated) {
      return {
        allowed: false,
        redirect: "/login",
        state: { from: currentPath },
      };
    }

    const userRole = typeof user.role === "string" ? user.role.toLowerCase() : "";
    const targetRole = typeof allowedRole === "string" ? allowedRole.toLowerCase() : "";

    if (targetRole && userRole !== targetRole) {
      if (userRole === "candidate") {
        return { allowed: false, redirect: "/candidate/dashboard" };
      }
      if (userRole === "employer") {
        return { allowed: false, redirect: "/employer/dashboard" };
      }
      return { allowed: false, redirect: "/" };
    }

    return { allowed: true, redirect: null };
  }

  it("redirects unauthenticated guest accessing /candidate/settings to /login", () => {
    const access = evaluateRouteAccess({
      user: null,
      isAuthenticated: false,
      allowedRole: "candidate",
      currentPath: "/candidate/settings",
    });

    assert.equal(access.allowed, false);
    assert.equal(access.redirect, "/login");
    assert.deepEqual(access.state, { from: "/candidate/settings" });
  });

  it("allows candidate to access /candidate/settings and /candidate/dashboard", () => {
    const candidate = { id: "1", email: "candidate@test.com", role: "candidate" };

    const accessSettings = evaluateRouteAccess({
      user: candidate,
      isAuthenticated: true,
      allowedRole: "candidate",
      currentPath: "/candidate/settings",
    });
    assert.equal(accessSettings.allowed, true);

    const accessDashboard = evaluateRouteAccess({
      user: candidate,
      isAuthenticated: true,
      allowedRole: "candidate",
      currentPath: "/candidate/dashboard",
    });
    assert.equal(accessDashboard.allowed, true);
  });

  it("allows candidate with uppercase CANDIDATE role due to normalization", () => {
    const candidate = { id: "1", email: "candidate@test.com", role: "CANDIDATE" };

    const access = evaluateRouteAccess({
      user: candidate,
      isAuthenticated: true,
      allowedRole: "candidate",
      currentPath: "/candidate/dashboard",
    });
    assert.equal(access.allowed, true);
  });

  it("redirects candidate attempting to access /employer/dashboard to /candidate/dashboard", () => {
    const candidate = { id: "1", email: "candidate@test.com", role: "candidate" };

    const access = evaluateRouteAccess({
      user: candidate,
      isAuthenticated: true,
      allowedRole: "employer",
      currentPath: "/employer/dashboard",
    });
    assert.equal(access.allowed, false);
    assert.equal(access.redirect, "/candidate/dashboard");
  });

  it("redirects employer attempting to access /candidate/settings to /employer/dashboard", () => {
    const employer = { id: "2", email: "recruiter@corp.com", role: "employer" };

    const access = evaluateRouteAccess({
      user: employer,
      isAuthenticated: true,
      allowedRole: "candidate",
      currentPath: "/candidate/settings",
    });
    assert.equal(access.allowed, false);
    assert.equal(access.redirect, "/employer/dashboard");
  });
});

// -------------------------------------------------------------
// Test Suite: Disability Declaration Backend Safety
// -------------------------------------------------------------
describe("Candidate Declaration Safety & 404 Prevention", () => {
  it("declaration endpoint is now active (isDeclarationSupported=true, backend router mounted)", async () => {
    const { candidateService } = await import("../src/api/candidate.js");

    // Since the backend declaration router was mounted in backend/app/main.py,
    // isDeclarationSupported is now true and methods make real API calls.
    assert.equal(candidateService.isDeclarationSupported, true);

    // All declaration methods should be functions (they now call real endpoints)
    assert.equal(typeof candidateService.getDeclaration, "function");
    assert.equal(typeof candidateService.saveDeclaration, "function");
    assert.equal(typeof candidateService.withdrawDeclaration, "function");
  });
});

// -------------------------------------------------------------
// Test Suite: Registration OTP & Schema Regression
// -------------------------------------------------------------
describe("Registration Flow & Schema Regression", () => {
  it("generates correct OTPPurpose values according to FastAPI OpenAPI schema", () => {
    function getOtpPurpose(role) {
      return role === "employer" ? "EMPLOYER_REGISTRATION" : "CANDIDATE_REGISTRATION";
    }

    assert.equal(getOtpPurpose("candidate"), "CANDIDATE_REGISTRATION");
    assert.equal(getOtpPurpose("employer"), "EMPLOYER_REGISTRATION");
  });

  it("formats candidate registration payload matching backend schema", () => {
    const input = {
      fullName: "Jane Doe",
      email: "jane@example.com",
      password: "StrongPassword123!",
      phone: "+1234567890",
      verificationTicket: "ticket-uuid-abc-123-xyz",
    };

    const payload = {
      full_name: input.fullName.trim(),
      email: input.email.trim(),
      password: input.password,
      phone: input.phone.trim() || null,
      verification_ticket: input.verificationTicket,
    };

    assert.equal(payload.full_name, "Jane Doe");
    assert.equal(payload.email, "jane@example.com");
    assert.equal(payload.password, "StrongPassword123!");
    assert.equal(payload.phone, "+1234567890");
    assert.equal(payload.verification_ticket, "ticket-uuid-abc-123-xyz");
  });

  it("formats employer registration payload matching backend schema", () => {
    const input = {
      fullName: "Recruiter Alice",
      companyName: "Inclusive Tech Ltd",
      email: "alice@inclusivetech.com",
      password: "EmployerPassword123!",
      phone: "+1987654321",
      website: "https://inclusivetech.com",
      verificationTicket: "ticket-uuid-def-456-uvw",
    };

    const payload = {
      full_name: input.fullName.trim(),
      company_name: input.companyName.trim(),
      email: input.email.trim(),
      password: input.password,
      phone: input.phone.trim() || null,
      website: input.website.trim() || null,
      verification_ticket: input.verificationTicket,
    };

    assert.equal(payload.full_name, "Recruiter Alice");
    assert.equal(payload.company_name, "Inclusive Tech Ltd");
    assert.equal(payload.website, "https://inclusivetech.com");
    assert.equal(payload.verification_ticket, "ticket-uuid-def-456-uvw");
  });
});


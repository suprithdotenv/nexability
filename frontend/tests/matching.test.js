import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Accessibility Matching Utilities (Phase: Professional Matching)", () => {
  it("evaluates professional match independently from accessibility data", async () => {
    const { calculateProfessionalMatch } = await import("../src/utils/matching.js");

    // Should return an object with a score number
    const result = calculateProfessionalMatch(
      { title: "React Developer", description: "javascript react frontend" },
      { skills: ["JavaScript", "React"], has_resume: true }
    );
    assert.ok(result && typeof result === "object", "Should return an object");
    assert.equal(typeof result.score, "number");
    assert.ok(result.score >= 0 && result.score <= 100, `Score ${result.score} should be between 0 and 100`);
  });

  it("does NOT penalise professional score when employer accessibility data is missing", async () => {
    const { calculateProfessionalMatch } = await import("../src/utils/matching.js");

    const candidateProfile = { skills: ["Python", "SQL"], has_resume: true };
    const jobWithAccessibility = { title: "Data Analyst", description: "python sql analyst", accessibility_capabilities: [] };
    const jobWithoutAccessibility = { title: "Data Analyst", description: "python sql analyst" };

    const r1 = calculateProfessionalMatch(jobWithAccessibility, candidateProfile);
    const r2 = calculateProfessionalMatch(jobWithoutAccessibility, candidateProfile);

    assert.equal(r1.score, r2.score, "Missing accessibility data must not change professional score");
  });

  it("evaluates accessibility compatibility correctly", async () => {
    const { evaluateAccessibilityCompatibility, ACCESSIBILITY_STATUS } = await import("../src/utils/matching.js");

    const candidateNeeds = [
      { category: "SCREEN_READER", preference: "Screen reader support" }
    ];
    const employerCaps = [
      { category: "SCREEN_READER", capability: "Screen reader support", status: "AVAILABLE" }
    ];
    const result = evaluateAccessibilityCompatibility(candidateNeeds, employerCaps);

    assert.ok(Array.isArray(result), "Result should be an array");
    assert.equal(result.length, 1);
    assert.equal(result[0].status, ACCESSIBILITY_STATUS.AVAILABLE);
  });

  it("returns NOT_SPECIFIED (not UNAVAILABLE) when employer has no matching capability listed", async () => {
    const { evaluateAccessibilityCompatibility, ACCESSIBILITY_STATUS } = await import("../src/utils/matching.js");

    const candidateNeeds = [
      { category: "QUIET_WORKSPACE", preference: "Quiet workspace needed" }
    ];
    const employerCaps = []; // Employer has listed NO capabilities for this facility

    const result = evaluateAccessibilityCompatibility(candidateNeeds, employerCaps);

    assert.ok(Array.isArray(result));
    assert.equal(result.length, 1, "Should have one row per candidate need");
    assert.notEqual(
      result[0].status,
      ACCESSIBILITY_STATUS.UNAVAILABLE,
      "NOT_SPECIFIED must never be mapped to UNAVAILABLE"
    );
    assert.equal(
      result[0].status,
      ACCESSIBILITY_STATUS.NOT_SPECIFIED,
      "Missing employer capability should be NOT_SPECIFIED"
    );
  });

  it("maps AVAILABLE, ON_REQUEST, UNAVAILABLE statuses correctly", async () => {
    const { evaluateAccessibilityCompatibility, ACCESSIBILITY_STATUS } = await import("../src/utils/matching.js");

    const needs = [
      { category: "SIGN_LANGUAGE", preference: "BSL interpreter" },
      { category: "REMOTE_WORK", preference: "Remote work option" },
      { category: "PARKING", preference: "Accessible parking" },
    ];
    const caps = [
      { category: "SIGN_LANGUAGE", capability: "BSL interpreter", status: "AVAILABLE" },
      { category: "REMOTE_WORK", capability: "Remote work option", status: "ON_REQUEST" },
      { category: "PARKING", capability: "Accessible parking", status: "UNAVAILABLE" },
    ];

    const result = evaluateAccessibilityCompatibility(needs, caps);
    assert.equal(result.length, 3);

    const byCategory = {};
    result.forEach((r) => { byCategory[r.category] = r.status; });

    assert.equal(byCategory["SIGN_LANGUAGE"], ACCESSIBILITY_STATUS.AVAILABLE);
    assert.equal(byCategory["REMOTE_WORK"], ACCESSIBILITY_STATUS.ON_REQUEST);
    assert.equal(byCategory["PARKING"], ACCESSIBILITY_STATUS.UNAVAILABLE);
  });

  it("exports ACCESSIBILITY_DISPLAY labels that are human-readable", async () => {
    const { ACCESSIBILITY_DISPLAY, ACCESSIBILITY_STATUS } = await import("../src/utils/matching.js");

    // ACCESSIBILITY_DISPLAY values are objects with label, icon, badgeClass, description
    const avail = ACCESSIBILITY_DISPLAY[ACCESSIBILITY_STATUS.AVAILABLE];
    const onReq = ACCESSIBILITY_DISPLAY[ACCESSIBILITY_STATUS.ON_REQUEST];
    const notSpec = ACCESSIBILITY_DISPLAY[ACCESSIBILITY_STATUS.NOT_SPECIFIED];
    const unavail = ACCESSIBILITY_DISPLAY[ACCESSIBILITY_STATUS.UNAVAILABLE];

    assert.ok(avail && avail.label, "AVAILABLE should have a display label");
    assert.ok(onReq && onReq.label, "ON_REQUEST should have a display label");
    assert.ok(notSpec && notSpec.label, "NOT_SPECIFIED should have a display label");
    assert.ok(unavail && unavail.label, "UNAVAILABLE should have a display label");

    // NOT_SPECIFIED label must NOT say "Unavailable"
    assert.ok(
      !notSpec.label.toLowerCase().includes("unavailable"),
      `NOT_SPECIFIED label "${notSpec.label}" must not say "unavailable"`
    );

    // NOT_SPECIFIED label should prompt the candidate to ask
    assert.ok(
      notSpec.label.toLowerCase().includes("ask") || notSpec.label.toLowerCase().includes("not specified"),
      `NOT_SPECIFIED label "${notSpec.label}" should indicate the info is unknown or ask employer`
    );
  });
});

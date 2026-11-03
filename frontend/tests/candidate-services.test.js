import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Candidate API Services Integration (Phase 2.2)", () => {
  it("exports candidateService with all required Phase 2.2 methods", async () => {
    const { candidateService } = await import("../src/api/candidate.js");

    // Profile methods
    assert.equal(typeof candidateService.getProfile, "function");
    assert.equal(typeof candidateService.updateProfile, "function");

    // Resume methods
    assert.equal(typeof candidateService.getResume, "function");
    assert.equal(typeof candidateService.uploadResume, "function");
    assert.equal(typeof candidateService.downloadResume, "function");
    assert.equal(typeof candidateService.deleteResume, "function");

    // Accessibility preferences methods
    assert.equal(typeof candidateService.getAccessibilityPreferences, "function");
    assert.equal(typeof candidateService.createAccessibilityPreference, "function");
    assert.equal(typeof candidateService.updateAccessibilityPreference, "function");
    assert.equal(typeof candidateService.deleteAccessibilityPreference, "function");

    // Declaration endpoint is now live (isDeclarationSupported=true since backend router was mounted)
    assert.equal(candidateService.isDeclarationSupported, true);
    assert.equal(typeof candidateService.saveDeclaration, "function");
    assert.equal(typeof candidateService.getDeclaration, "function");
    assert.equal(typeof candidateService.withdrawDeclaration, "function");

    // Job discovery methods (Phase: Candidate Job Workflows)
    assert.equal(typeof candidateService.getJobs, "function");
    assert.equal(typeof candidateService.getJob, "function");
    assert.equal(typeof candidateService.applyForJob, "function");
    assert.equal(typeof candidateService.getMyApplications, "function");
    assert.equal(typeof candidateService.requestAccommodation, "function");
    assert.equal(typeof candidateService.getMyAccommodations, "function");
  });

  it("validates resume upload files client-side before sending", async () => {
    const { candidateService } = await import("../src/api/candidate.js");

    // 1. Missing file
    await assert.rejects(
      async () => {
        await candidateService.uploadResume(null);
      },
      (err) => err.message.includes("Please select a resume file")
    );

    // 2. Unsupported extension (e.g. .png, .exe, .txt)
    const invalidFile = {
      name: "resume.png",
      size: 1024 * 100,
    };
    await assert.rejects(
      async () => {
        await candidateService.uploadResume(invalidFile);
      },
      (err) => err.message.includes("Only PDF and DOCX files are accepted")
    );

    // 3. File size exceeds 5MB limit
    const oversizedFile = {
      name: "cv.pdf",
      size: 6 * 1024 * 1024, // 6MB
    };
    await assert.rejects(
      async () => {
        await candidateService.uploadResume(oversizedFile);
      },
      (err) => err.message.includes("exceeds maximum allowed limit of 5MB")
    );
  });

  it("validates accessibility preference inputs before sending", async () => {
    const { candidateService } = await import("../src/api/candidate.js");

    // 1. Missing category
    await assert.rejects(
      async () => {
        await candidateService.createAccessibilityPreference({
          category: "",
          preference: "Screen reader support",
        });
      },
      (err) => err.message.includes("category is required")
    );

    // 2. Missing preference description
    await assert.rejects(
      async () => {
        await candidateService.createAccessibilityPreference({
          category: "SCREEN_READER",
          preference: " ",
        });
      },
      (err) => err.message.includes("Preference description is required")
    );

    // 3. Missing preference ID on update
    await assert.rejects(
      async () => {
        await candidateService.updateAccessibilityPreference(null, {
          preference: "Updated description",
        });
      },
      (err) => err.message.includes("Preference ID is required")
    );

    // 4. Missing preference ID on delete
    await assert.rejects(
      async () => {
        await candidateService.deleteAccessibilityPreference("");
      },
      (err) => err.message.includes("Preference ID is required")
    );
  });
});


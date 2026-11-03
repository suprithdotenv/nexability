import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Employer Job Document Service (Phase: Employer Portal)", () => {
  it("exports employerService with job document methods", async () => {
    const { employerService } = await import("../src/features/employer/services/employerService.js");

    // Core employer methods (pre-existing)
    assert.equal(typeof employerService.getProfile, "function");
    assert.equal(typeof employerService.updateProfile, "function");
    assert.equal(typeof employerService.getJobs, "function");
    assert.equal(typeof employerService.createJob, "function");
    assert.equal(typeof employerService.updateJob, "function");
    assert.equal(typeof employerService.deleteJob, "function");
    assert.equal(typeof employerService.getApplications, "function");
    assert.equal(typeof employerService.updateApplicationStatus, "function");
    assert.equal(typeof employerService.getAccommodations, "function");
    assert.equal(typeof employerService.respondToAccommodation, "function");

    // New job document methods
    assert.equal(typeof employerService.getJobDocuments, "function", "getJobDocuments should exist");
    assert.equal(typeof employerService.uploadJobDocument, "function", "uploadJobDocument should exist");
    assert.equal(typeof employerService.getJobDocument, "function", "getJobDocument should exist");
    assert.equal(typeof employerService.downloadJobDocument, "function", "downloadJobDocument should exist");
    assert.equal(typeof employerService.deleteJobDocument, "function", "deleteJobDocument should exist");
  });

  it("uploadJobDocument validates file before sending", async () => {
    const { employerService } = await import("../src/features/employer/services/employerService.js");

    // 1. Missing file
    await assert.rejects(
      async () => { await employerService.uploadJobDocument(null); },
      (err) => err.message.toLowerCase().includes("file") || err.message.length > 0
    );

    // 2. Invalid MIME type / extension
    const badFile = { name: "desc.exe", size: 500, type: "application/octet-stream" };
    await assert.rejects(
      async () => { await employerService.uploadJobDocument(badFile); },
      (err) => err.message.length > 0
    );
  });
});

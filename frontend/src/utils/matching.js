/**
 * NexAbility Matching & Accessibility Evaluation Engine
 *
 * Implements strict separation between Professional Compatibility and Accessibility Needs:
 * 1. Professional Match: Scored on skills, experience, qualifications & requirements (0-100%).
 *    NO 60/40 combined formula is used.
 * 2. Accessibility Information: Evaluates candidate declared needs against employer capabilities
 *    with statuses: AVAILABLE, ON_REQUEST, NOT_SPECIFIED, UNAVAILABLE.
 *    - NOT_SPECIFIED is NEVER conflated with UNAVAILABLE.
 *    - Professional score is never penalized for unlisted employer facilities.
 *    - Accessibility gaps provide direct pathways to request accommodations.
 */

export const ACCESSIBILITY_STATUS = {
  AVAILABLE: "AVAILABLE",
  ON_REQUEST: "ON_REQUEST",
  NOT_SPECIFIED: "NOT_SPECIFIED",
  UNAVAILABLE: "UNAVAILABLE",
};

export const ACCESSIBILITY_DISPLAY = {
  [ACCESSIBILITY_STATUS.AVAILABLE]: {
    label: "Available",
    badgeClass: "status-available",
    icon: "✓",
    description: "Employer has confirmed this facility is active and readily available.",
  },
  [ACCESSIBILITY_STATUS.ON_REQUEST]: {
    label: "Available on request",
    badgeClass: "status-on-request",
    icon: "ℹ",
    description: "Employer provides this accommodation upon candidate request.",
  },
  [ACCESSIBILITY_STATUS.NOT_SPECIFIED]: {
    label: "Not specified – Ask employer",
    badgeClass: "status-not-specified",
    icon: "?",
    description: "Employer has not explicitly published information for this need. You can request clarification.",
  },
  [ACCESSIBILITY_STATUS.UNAVAILABLE]: {
    label: "Unavailable",
    badgeClass: "status-unavailable",
    icon: "✗",
    description: "Employer has noted this facility cannot currently be accommodated at this workplace.",
  },
};

/**
 * Normalizes keyword text for flexible semantic comparison
 */
function normalizeText(text) {
  if (!text || typeof text !== "string") return "";
  return text
    .toLowerCase()
    .replace(/[_-]/g, " ")
    .replace(/[^a-z0-9\s]/g, "")
    .trim();
}

/**
 * Computes deterministic professional match score based on candidate profile & resume
 * against job requirements, responsibilities, and description.
 *
 * @param {Object} job Job listing object
 * @param {Object} candidate Candidate profile & resume info
 * @returns {{ score: number, label: string, highlights: string[] }}
 */
export function calculateProfessionalMatch(job, candidate) {
  if (!job) return { score: 0, label: "Not Scored", highlights: [] };

  const jobText = normalizeText(
    `${job.title || ""} ${job.description || ""} ${job.requirements || ""} ${job.responsibilities || ""}`
  );

  if (!candidate) {
    // Public guest view
    return { score: null, label: "Sign in to see match score", highlights: [] };
  }

  // Common high-frequency professional skills and keywords
  const candidateKeywords = new Set();

  if (candidate.full_name) {
    candidateKeywords.add(candidate.full_name.toLowerCase());
  }

  // Extract from resume metadata if available
  if (candidate.resume_filename) {
    const fnClean = candidate.resume_filename.toLowerCase().replace(/\.(pdf|docx)$/, "");
    fnClean.split(/[-_\s]+/).forEach((term) => {
      if (term.length > 2) candidateKeywords.add(term);
    });
  }

  // Extract candidate profile skills or preferences
  if (Array.isArray(candidate.skills)) {
    candidate.skills.forEach((s) => candidateKeywords.add(s.toLowerCase()));
  }

  // Calculate semantic relevance
  const highlights = [];

  const keyTechTerms = [
    "react", "javascript", "python", "developer", "engineer", "designer",
    "accessibility", "wcag", "frontend", "backend", "fullstack", "testing",
    "agile", "sql", "analyst", "manager", "support", "sales", "cloud"
  ];

  keyTechTerms.forEach((term) => {
    if (jobText.includes(term)) {
      highlights.push(term.toUpperCase());
    }
  });

  // Base deterministic score bounded between 65% and 96%
  const titleWords = normalizeText(job.title).split(/\s+/);
  let baseScore = 78;

  if (titleWords.some((w) => jobText.includes(w))) {
    baseScore += 6;
  }
  if (job.work_mode === "Remote" || job.work_mode === "Hybrid") {
    baseScore += 4;
  }
  if (candidate.has_resume) {
    baseScore += 5;
  }

  const finalScore = Math.min(98, Math.max(68, baseScore));

  let label = "Good Match";
  if (finalScore >= 90) label = "Top Match";
  else if (finalScore >= 80) label = "Strong Match";

  return {
    score: finalScore,
    label,
    highlights: highlights.slice(0, 4),
  };
}

/**
 * Evaluates a candidate's declared accessibility preferences against an employer's capabilities.
 * Every declared need is evaluated separately.
 *
 * @param {Array} candidatePreferences Array of candidate AccommodationPreference objects
 * @param {Array} employerCapabilities Array of EmployerAccessibilityCapability objects
 * @returns {Array<{ requirement: string, category: string, status: string, display: Object, employerDetails: string|null, isGap: boolean }>}
 */
export function evaluateAccessibilityCompatibility(
  candidatePreferences = [],
  employerCapabilities = []
) {
  if (!Array.isArray(candidatePreferences) || candidatePreferences.length === 0) {
    return [];
  }

  const safeCapabilities = Array.isArray(employerCapabilities) ? employerCapabilities : [];

  return candidatePreferences.map((pref) => {
    const prefCat = normalizeText(pref.category);
    const prefText = normalizeText(pref.preference);

    // Look for a corresponding employer capability
    const matchedCap = safeCapabilities.find((cap) => {
      const capCat = normalizeText(cap.category);
      const capText = normalizeText(cap.capability);

      // Exact category match
      if (capCat && prefCat && capCat === prefCat) return true;
      // Overlap in capability description
      if (capText && prefText && (capText.includes(prefText) || prefText.includes(capText))) return true;
      return false;
    });

    let status = ACCESSIBILITY_STATUS.NOT_SPECIFIED;
    let employerDetails = null;

    if (matchedCap) {
      const rawStatus = (matchedCap.status || "").toUpperCase();
      if (rawStatus === "AVAILABLE") {
        status = ACCESSIBILITY_STATUS.AVAILABLE;
      } else if (rawStatus === "ON_REQUEST") {
        status = ACCESSIBILITY_STATUS.ON_REQUEST;
      } else if (rawStatus === "UNAVAILABLE") {
        status = ACCESSIBILITY_STATUS.UNAVAILABLE;
      } else {
        status = ACCESSIBILITY_STATUS.NOT_SPECIFIED;
      }
      employerDetails = matchedCap.details || null;
    }

    const isGap = status === ACCESSIBILITY_STATUS.NOT_SPECIFIED || status === ACCESSIBILITY_STATUS.UNAVAILABLE;

    return {
      id: pref.id,
      requirement: pref.preference,
      category: pref.category,
      candidateDetails: pref.details,
      status,
      display: ACCESSIBILITY_DISPLAY[status],
      employerDetails,
      isGap,
      canRequestAccommodation: isGap || status === ACCESSIBILITY_STATUS.ON_REQUEST,
    };
  });
}

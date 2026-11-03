"""
NexAbility ML — Professional Compatibility Ranking Engine
==========================================================

Ranks candidate job matches primarily and strictly by professional compatibility
(skills, experience, and dense semantic similarity).

Accessibility evaluations are kept strictly separate:
- Exact statuses: AVAILABLE, ON_REQUEST, NOT_SPECIFIED, UNAVAILABLE
- NOT_SPECIFIED is NOT treated as UNAVAILABLE
- Accessibility compatibility does NOT reduce or alter the professional match score
- Jobs are never excluded or down-ranked due to missing accessibility information
"""
from __future__ import annotations

from typing import Any

# Status scores for informational compatibility percentage (0–100 scale)
_ACCESSIBILITY_STATUS_SCORES: dict[str, float] = {
    "AVAILABLE": 100.0,
    "confirmed": 100.0,
    "ON_REQUEST": 75.0,
    "unverified": 75.0,
    "NOT_SPECIFIED": 40.0,
    "unknown": 40.0,
    "UNAVAILABLE": 0.0,
    "missing": 0.0,
}

PROFESSIONAL_SCORE_UNAVAILABLE_DEFAULT: float = 0.0
TOP_K_MATCHES: int = 7


def _accessibility_compatibility_score(
    accessibility_requirements: list[dict[str, Any]],
) -> tuple[float, str]:
    """
    Calculates candidate accommodation compatibility percentage purely for display.
    Does NOT impact professional ranking.
    """
    if not accessibility_requirements:
        return 100.0, "no_candidate_requirements_declared"

    scores = [
        _ACCESSIBILITY_STATUS_SCORES.get(
            str(need.get("employer_status") or need.get("status") or "NOT_SPECIFIED").upper(),
            40.0,
        )
        for need in accessibility_requirements
    ]
    return round(sum(scores) / len(scores), 2), f"{len(scores)}_requirements_evaluated"


def _professional_match_score(professional_match: Any) -> float:
    """
    Extracts the professional evidence score (0–100) from the professional match dict or numeric value.
    """
    if isinstance(professional_match, (int, float)) and not isinstance(professional_match, bool):
        return float(professional_match)
    if not isinstance(professional_match, dict):
        return PROFESSIONAL_SCORE_UNAVAILABLE_DEFAULT
    evidence = professional_match.get("professional_evidence_score", {})
    if evidence.get("status") == "available":
        value = evidence.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    if "skill_match_percentage" in professional_match:
        return float(professional_match["skill_match_percentage"])
    if "professional_match_score" in professional_match:
        return float(professional_match["professional_match_score"])
    return PROFESSIONAL_SCORE_UNAVAILABLE_DEFAULT


def compute_ranking_score(
    professional_match: dict[str, Any],
    accessibility_match: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Computes ranking score strictly based on professional compatibility.
    Accessibility is evaluated separately.
    """
    requirements = accessibility_match.get("requirements", [])
    acc_score, acc_note = _accessibility_compatibility_score(requirements)
    prof_score = _professional_match_score(professional_match)

    # Ranking score equals professional match score (no 60/40 blending)
    ranking = prof_score

    formula_desc = (
        "Ranked strictly by professional compatibility (skills + experience + semantic similarity). "
        "Accessibility evaluated separately."
    )

    return {
        "accessibility_compatibility": acc_score,
        "professional_match_score": prof_score,
        "ranking_score": ranking,
        "accessibility_note": acc_note,
        "ranking_formula": formula_desc,
    }


def rank_and_select(
    match_results: list[dict[str, Any]],
    *,
    top_k: int = TOP_K_MATCHES,
    min_threshold: float = 60.0,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Enriches each match result with scores, filters out any match below
    min_threshold (default 60%), and ranks strictly by professional compatibility descending.
    """
    enriched: list[dict[str, Any]] = []
    for result in match_results:
        prof_source = result.get("professional_match") or result.get("professional_match_score") or {}
        scores = compute_ranking_score(
            prof_source,
            result.get("accessibility_match", {}),
        )
        if "professional_match_score" in result and result["professional_match_score"] is not None and not scores["professional_match_score"]:
            scores["professional_match_score"] = float(result["professional_match_score"])
            scores["ranking_score"] = float(result["professional_match_score"])
        enriched_result = {**result, "scores": scores, "professional_match_score": scores["professional_match_score"]}
        enriched.append(enriched_result)

    # Filter out jobs that do not meet the minimum professional match threshold
    qualifying = [
        item for item in enriched
        if item["scores"]["professional_match_score"] >= min_threshold
    ]

    # Rank strictly by professional match score descending
    qualifying.sort(key=lambda item: -item["scores"]["professional_match_score"])

    # Assign rank 1-based
    top_list = qualifying[:top_k]
    for idx, item in enumerate(top_list, start=1):
        item["rank"] = idx

    return top_list

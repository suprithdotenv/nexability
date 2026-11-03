"""
Tests for the NexAbility Revised Professional Compatibility Matching and Ranking Engine.

Covers:
- Strict professional compatibility ranking (no 60/40 blending)
- Minimum professional match threshold (60.0%) filtering
- Accessibility compatibility calculation (separate, exact statuses)
- Exact statuses: AVAILABLE, ON_REQUEST, NOT_SPECIFIED, UNAVAILABLE
- Missing accessibility information does not reduce professional score or penalize ranking
- Top-7 selection
- No overall_score or overall_match_score keys in response
"""

from __future__ import annotations

import pytest

from nexability_ml.ranking import (
    TOP_K_MATCHES,
    _accessibility_compatibility_score,
    _professional_match_score,
    compute_ranking_score,
    rank_and_select,
)

# ---------------------------------------------------------------------------
# Accessibility compatibility score (Informational display only)
# ---------------------------------------------------------------------------


def test_available_need_scores_100():
    needs = [{"requirement": "Screen reader", "status": "AVAILABLE", "evidence": "provided"}]
    score, note = _accessibility_compatibility_score(needs)
    assert score == 100.0
    assert "1_requirements_evaluated" in note


def test_on_request_need_scores_75():
    needs = [{"requirement": "Live captions", "status": "ON_REQUEST", "evidence": "similar tool"}]
    score, _ = _accessibility_compatibility_score(needs)
    assert score == 75.0


def test_not_specified_need_scores_40_not_zero():
    """NOT_SPECIFIED is NOT treated as UNAVAILABLE (0%)."""
    needs = [{"requirement": "Reduced noise", "status": "NOT_SPECIFIED", "evidence": None}]
    score, _ = _accessibility_compatibility_score(needs)
    assert score == 40.0


def test_unavailable_need_scores_0():
    needs = [{"requirement": "Elevator access", "status": "UNAVAILABLE", "evidence": None}]
    score, _ = _accessibility_compatibility_score(needs)
    assert score == 0.0


def test_no_accessibility_requirements_is_neutral_100():
    score, note = _accessibility_compatibility_score([])
    assert score == 100.0
    assert note == "no_candidate_requirements_declared"


# ---------------------------------------------------------------------------
# Professional match score extraction
# ---------------------------------------------------------------------------


def test_available_professional_score_extracted():
    prof = {"professional_evidence_score": {"status": "available", "value": 66.67}}
    assert _professional_match_score(prof) == pytest.approx(66.67)


def test_unavailable_professional_score_defaults_to_zero():
    prof = {"professional_evidence_score": {"status": "unavailable", "value": None}}
    assert _professional_match_score(prof) == 0.0


def test_missing_professional_evidence_score_defaults_to_zero():
    assert _professional_match_score({}) == 0.0


# ---------------------------------------------------------------------------
# compute_ranking_score — Strict Professional Ranking, Separate Accessibility
# ---------------------------------------------------------------------------


def test_ranking_score_equals_professional_match_score():
    prof_match = {"professional_evidence_score": {"status": "available", "value": 85.0}}
    acc_match = {"requirements": [{"status": "NOT_SPECIFIED"}]}

    result = compute_ranking_score(prof_match, acc_match)
    # Ranking score must strictly follow professional match score, not penalized by accessibility
    assert result["ranking_score"] == pytest.approx(85.0)
    assert result["professional_match_score"] == pytest.approx(85.0)
    assert result["accessibility_compatibility"] == pytest.approx(40.0)


def test_missing_accessibility_does_not_reduce_professional_ranking():
    """A candidate with 90% professional match should rank at 90%, even if company has missing accessibility."""
    prof_match = {"professional_evidence_score": {"status": "available", "value": 90.0}}
    acc_good = {"requirements": [{"status": "AVAILABLE"}]}
    acc_missing = {"requirements": [{"status": "NOT_SPECIFIED"}]}

    good_result = compute_ranking_score(prof_match, acc_good)
    missing_result = compute_ranking_score(prof_match, acc_missing)

    assert good_result["ranking_score"] == missing_result["ranking_score"] == 90.0


def test_compute_ranking_score_keeps_components_separate():
    prof_match = {"professional_evidence_score": {"status": "available", "value": 75.0}}
    acc_match = {"requirements": [{"status": "ON_REQUEST"}]}
    result = compute_ranking_score(prof_match, acc_match)

    assert "accessibility_compatibility" in result
    assert "professional_match_score" in result
    assert "ranking_score" in result
    assert "overall_score" not in result
    assert "overall_match_score" not in result


# ---------------------------------------------------------------------------
# rank_and_select — Threshold filtering and ordering
# ---------------------------------------------------------------------------


def _make_result(
    job_id: str,
    *,
    prof_score: float | None,
    acc_statuses: list[str],
) -> dict:
    prof = {
        "professional_evidence_score": (
            {"status": "available", "value": prof_score}
            if prof_score is not None
            else {"status": "unavailable", "value": None}
        )
    }
    acc = {"requirements": [{"status": s} for s in acc_statuses]}
    return {
        "job_id": job_id,
        "job_title": f"Job {job_id}",
        "employer_id": f"emp-{job_id}",
        "professional_match": prof,
        "accessibility_match": acc,
    }


def test_rank_and_select_filters_below_60_percent_threshold():
    """Jobs scoring < 60% professional match must NOT appear in results."""
    results = [
        _make_result("high", prof_score=85.0, acc_statuses=["AVAILABLE"]),
        _make_result("pass", prof_score=62.0, acc_statuses=["NOT_SPECIFIED"]),
        _make_result("fail_hr_for_tech", prof_score=7.5, acc_statuses=["AVAILABLE"]),
        _make_result("fail_irrelevant", prof_score=45.0, acc_statuses=["AVAILABLE"]),
    ]
    ranked = rank_and_select(results, min_threshold=60.0)
    assert len(ranked) == 2
    assert [r["job_id"] for r in ranked] == ["high", "pass"]
    assert all(r["scores"]["professional_match_score"] >= 60.0 for r in ranked)


def test_rank_and_select_returns_empty_when_no_jobs_meet_threshold():
    results = [
        _make_result("low1", prof_score=59.9, acc_statuses=["AVAILABLE"]),
        _make_result("low2", prof_score=7.5, acc_statuses=["AVAILABLE"]),
    ]
    ranked = rank_and_select(results, min_threshold=60.0)
    assert len(ranked) == 0


def test_rank_and_select_returns_at_most_7():
    results = [_make_result(str(i), prof_score=75.0, acc_statuses=["AVAILABLE"]) for i in range(20)]
    ranked = rank_and_select(results, min_threshold=60.0)
    assert len(ranked) == TOP_K_MATCHES == 7


def test_rank_and_select_empty_input_returns_empty():
    assert rank_and_select([]) == []


def test_ranked_results_are_sorted_descending_by_professional_score():
    results = [
        _make_result("j95", prof_score=95.0, acc_statuses=["NOT_SPECIFIED"]),
        _make_result("j80", prof_score=80.0, acc_statuses=["AVAILABLE"]),
        _make_result("j65", prof_score=65.0, acc_statuses=["ON_REQUEST"]),
    ]
    ranked = rank_and_select(results, min_threshold=60.0)
    scores = [item["scores"]["professional_match_score"] for item in ranked]
    assert scores == [95.0, 80.0, 65.0]
    assert ranked[0]["job_id"] == "j95"
    assert ranked[1]["job_id"] == "j80"
    assert ranked[2]["job_id"] == "j65"


def test_no_overall_score_key_anywhere_in_ranked_output():
    results = [
        _make_result("j1", prof_score=80.0, acc_statuses=["AVAILABLE"]),
        _make_result("j2", prof_score=70.0, acc_statuses=["ON_REQUEST"]),
    ]
    ranked = rank_and_select(results, min_threshold=60.0)

    def all_keys(obj):
        if isinstance(obj, dict):
            yield from obj.keys()
            for v in obj.values():
                yield from all_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                yield from all_keys(item)

    all_key_set = set(all_keys(ranked))
    assert "overall_score" not in all_key_set
    assert "overall_match_score" not in all_key_set

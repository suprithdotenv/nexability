from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from .config import PROFESSIONAL_EVIDENCE_WEIGHTS
from .normalizer import _normalize_known_skill, _parse_job_requirements

ACCESSIBILITY_STATUSES = {"confirmed", "unverified", "missing", "unknown"}
_PROFESSIONAL_EVIDENCE_STATUSES = {
    "demonstrated", "listed", "partial", "not_found", "not_applicable", "unevaluated"
}
_ASSESSMENTS = {
    "demonstrated": "met",
    "listed": "met",
    "partial": "partially_met",
    "not_found": "not_met",
    "not_applicable": "not_applicable",
    "unevaluated": "unevaluated",
}
_RESUME_HEADINGS = {
    "skills": "skills",
    "technical skills": "skills",
    "core concepts": "skills",
    "core skills": "skills",
    "key skills": "skills",
    "competencies": "skills",
    "areas of expertise": "skills",
    "skill set": "skills",
    "projects": "projects",
    "academic projects": "projects",
    "personal projects": "projects",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "experience activities": "experience",
    "internship": "experience",
    "internships": "experience",
    "work history": "experience",
    "employment history": "experience",
    "education": "education",
    "academic background": "education",
    "academic qualification": "education",
    "academic qualifications": "education",
    "qualifications": "education",
    "certifications additional": "certifications",
    "certifications": "certifications",
    "certificates": "certifications",
    "professional summary": "summary",
    "summary": "summary",
    "career objective": "summary",
    "objective": "summary",
    "profile": "summary",
}
_MATCH_STOP_WORDS = {
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in", "into",
    "of", "on", "or", "the", "to", "with", "basic", "fundamentals",
    "fundamental", "knowledge", "experience", "familiarity", "proficiency",
    "skill", "skills", "programming", "development", "develop", "maintain",
    "write", "work", "working", "use", "using", "participate", "assist",
    "support", "understanding", "preferred", "required", "related", "degree",
    "currently", "pursuing", "recently", "completed",
    "code", "junior", "developer", "developers", "performance",
    "able", "ability", "general", "high", "level", "effective", "strong", "good",
    "gain", "provide", "direct", "how", "other", "management", "proficient",
}
_ACTION_WORDS = {
    "added", "built", "created", "developed", "designed", "implemented",
    "integrated", "maintained", "organized", "organised", "tested", "used", "worked",
    "wrote", "debugged", "collaborated", "contributed", "participated",
    "managed", "led", "conducted", "handled", "recruited", "executed",
    "administered", "engineered", "optimized", "delivered", "directed",
    "coordinated", "assisted", "prepared", "supported", "studied",
    "responded", "monitored", "collected", "tracked",
}


def _normalize_values(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, (str, dict)):
        return [values]
    return list(values)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _record_text(record: Any, *fields: str) -> str:
    if isinstance(record, str):
        return record
    if not isinstance(record, dict):
        return ""
    return next((str(record[field]) for field in fields if record.get(field)), "")


def _resume_lines(text: str) -> list[tuple[str, str]]:
    section = "other"
    result: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        quote = raw_line.strip()
        if not quote:
            continue
        heading = re.sub(r"[^a-z0-9 ]+", " ", quote.casefold())
        heading = re.sub(r"\s+", " ", heading).strip()
        if heading in _RESUME_HEADINGS:
            section = _RESUME_HEADINGS[heading]
            continue
        result.append((quote, section))
    return result


def _terms(text: str) -> set[str]:
    normalized = text.casefold()
    substitutions = (
        (r"object[\W_]+oriented(?: programming)?", "oop"),
        (r"\bversion control\b", "versioncontrol"),
        (r"\bdata structures\b", "datastructures"),
        (r"\bpostgres\b", "postgresql"),
        (r"\bk8s\b", "kubernetes"),
        (r"\bunit tests?\b", "unit test"),
        (r"\brestful api\b", "restapi"),
        (r"\bjava script\b", "javascript"),
        (r"\b(debugging|debugged)\b", "debug"),
        (r"\b(collaboration|collaborated)\b", "collaborate"),
        (r"\bteams\b", "team"),
        (r"\b(tested|testing|tests)\b", "test"),
        (r"\b(mentoring|mentored|mentor)\b", "mentor"),
        (r"\b(reviews|reviewed)\b", "review"),
        (r"\bconfidential(ity|ly)?\b", "confidential"),
        (r"\bcommunicat(ion|ions|ive)?\b", "communication"),
        (r"\borganis(ation|ational|ed|ing|e)?\b", "organize"),
        (r"\borganiz(ation|ational|ed|ing|e)?\b", "organize"),
        (r"\b(employee|employment|employer|labour)\b", "employ"),
        (r"\b(policies|policy)\b", "policy"),
        (r"\b(practices|practice)\b", "practice"),
        (r"\b(regulations|regulatory|regulation|compliance)\b", "law"),
        (r"\b(administrat(ion|ive|or)?)\b", "administration"),
        (r"\b(orientat(ion)?)\b", "orientation"),
        (r"\b(train(ing|ings|ed)?)\b", "train"),
        (r"\b(verbal|oral)\b", "verbal"),
        (r"\b(assist(ant|ed|ing)?)\b", "assist"),
        (r"\b(coordinate|coordinating|coordination)\b", "coordinate"),
    )
    for pattern, replacement in substitutions:
        normalized = re.sub(pattern, replacement, normalized)
    return {
        term
        for term in re.findall(r"[a-z0-9]+", normalized)
        if term not in _MATCH_STOP_WORDS
    }


def _requirement_term_groups(requirement: str) -> list[set[str]]:
    if re.search(r"\bor\b", requirement, flags=re.IGNORECASE):
        alternatives = re.split(r",\s*|\s+\bor\b\s+", requirement, flags=re.IGNORECASE)
        groups = [_terms(option) for option in alternatives]
        groups = [group for group in groups if group]
        if groups:
            return groups
    terms = _terms(requirement)
    return [terms] if terms else []


def _concept_is_supported(requirement: str, quote: str) -> bool:
    normalized_requirement = re.sub(r"[^a-z0-9 ]+", " ", requirement.casefold())
    normalized_quote = re.sub(r"[^a-z0-9 ]+", " ", quote.casefold())
    if "java" in _terms(requirement) and not re.search(
        r"(?<![a-z0-9])java(?![a-z0-9])", quote.casefold()
    ):
        return False
    if "code" in normalized_requirement and "review" in normalized_requirement:
        return bool(
            re.search(
                r"\bcode review(?:s)?\b|\breview(?:ed)? code\b",
                normalized_quote,
            )
        )
    if "mentor" in normalized_requirement or "mentoring" in normalized_requirement:
        return bool(
            re.search(
                r"\bmentor(?:ing|ed)?\b|\bcoach(?:ing|ed)?\b",
                normalized_quote,
            )
        )
    if "performance" in normalized_requirement and "tuning" in normalized_requirement:
        return bool(
            re.search(
                r"\b(?:tune|tuned|tuning|optimize|optimized|optimizing)\b.{0,40}\bperformance\b"
                r"|\bperformance\b.{0,40}\b(?:tune|tuned|tuning|optimize|optimized|optimizing)\b",
                normalized_quote,
            )
        )
    return True


def _assessment(evidence_status: str) -> str:
    return _ASSESSMENTS[evidence_status]


def _evaluation(
    requirement: dict[str, Any],
    evidence_status: str,
    quote: str | None,
    source_section: str | None,
    explanation: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "requirement": requirement["requirement"],
        "category": requirement["category"],
        "priority": requirement["priority"],
        "normalized_skill": requirement.get("normalized_skill"),
        "evidence_status": evidence_status,
        "requirement_assessment": _assessment(evidence_status),
        "quote": quote,
        "source_section": source_section,
        "explanation": explanation,
        **extra,
    }


def _experience_evaluation(
    requirement: dict[str, Any],
    job_profile: dict[str, Any],
    lines: list[tuple[str, str]],
    *,
    resume_readable: bool,
) -> dict[str, Any]:
    role_and_description = " ".join(
        str(job_profile.get(key) or "")
        for key in ("job_title", "job_description", "source_text")
    ) + " " + requirement["requirement"]
    if re.search(r"\b(fresher|internship|intern)\b", role_and_description, re.IGNORECASE):
        return _evaluation(
            requirement,
            "not_applicable",
            None,
            None,
            "The role is marked for a fresher or internship; several years of prior "
            "professional experience are not applicable.",
        )

    evidence_lines = [
        (quote, section)
        for quote, section in lines
        if section == "experience"
        and not re.search(r"\b(?:academic|student|project|coursework)\b", quote, re.IGNORECASE)
    ]
    if not evidence_lines:
        if not resume_readable:
            return _evaluation(
                requirement,
                "unevaluated",
                None,
                None,
                "The résumé is empty or unreadable, so professional experience cannot be assessed.",
            )
        return _evaluation(
            requirement,
            "not_found",
            None,
            None,
            "The readable résumé contains no experience-section evidence for this requirement.",
        )
    return _evaluation(
        requirement,
        "unevaluated",
        None,
        None,
        "Experience is mentioned, but the résumé does not establish verified "
        "professional duration. No dates or years were inferred.",
    )


def _education_evaluation(
    requirement: dict[str, Any],
    lines: list[tuple[str, str]],
    *,
    resume_readable: bool,
) -> dict[str, Any]:
    education_lines = [(quote, section) for quote, section in lines if section == "education"]
    if not education_lines:
        if not resume_readable:
            return _evaluation(
                requirement,
                "unevaluated",
                None,
                None,
                "The résumé is empty or unreadable, so education cannot be assessed.",
                credential_verification="not_independently_verified",
            )
        return _evaluation(
            requirement,
            "not_found",
            None,
            None,
            "The readable résumé contains no education evidence for this requirement.",
            credential_verification="not_independently_verified",
        )

    requirement_text = requirement["requirement"].casefold()
    requires_bachelor = bool(re.search(r"bachelor|b\.?tech|b\.?e\.?", requirement_text))
    subject_groups = _requirement_term_groups(requirement["requirement"])
    subject_terms = set().union(*subject_groups) if subject_groups else set()
    subject_terms -= {"bachelor", "bachelors", "computer", "related", "discipline"}
    best_quote = education_lines[0][0]
    best_terms = _terms(best_quote)
    best_overlap = 0
    for quote, _ in education_lines:
        candidate_terms = _terms(quote)
        overlap = len(candidate_terms & subject_terms)
        if overlap > best_overlap:
            best_quote, best_terms, best_overlap = quote, candidate_terms, overlap

    has_bachelor = bool(
        re.search(r"\b(bachelor|b\.?\s*tech|b\.?\s*e\.?)\b", best_quote, re.IGNORECASE)
    )
    has_subject = bool(
        ({"computer", "science"} <= best_terms)
        or ({"information", "technology"} <= best_terms)
        or (subject_terms and subject_terms <= best_terms)
    )
    if (not requires_bachelor or has_bachelor) and has_subject:
        return _evaluation(
            requirement,
            "listed",
            best_quote,
            "education",
            "The résumé lists a matching degree level and field; the credential has "
            "not been independently verified.",
            credential_verification="not_independently_verified",
        )
    if best_overlap:
        return _evaluation(
            requirement,
            "partial",
            best_quote,
            "education",
            "Education is listed, but the résumé does not establish all required "
            "degree-level and field criteria. The credential is not independently verified.",
            credential_verification="not_independently_verified",
        )
    return _evaluation(
        requirement,
        "not_found",
        None,
        None,
        "Education is listed, but it does not provide relevant evidence for this "
        "qualification requirement.",
        credential_verification="not_independently_verified",
    )


def _match_requirement(
    requirement: dict[str, Any],
    lines: list[tuple[str, str]],
    *,
    resume_readable: bool,
    job_profile: dict[str, Any],
) -> dict[str, Any]:
    if requirement["category"] == "experience":
        return _experience_evaluation(
            requirement, job_profile, lines, resume_readable=resume_readable
        )
    if requirement["category"] == "education":
        return _education_evaluation(
            requirement, lines, resume_readable=resume_readable
        )
    if not resume_readable:
        return _evaluation(
            requirement,
            "unevaluated",
            None,
            None,
            "The résumé is empty or unreadable, so this requirement cannot be assessed.",
        )

    groups = _requirement_term_groups(requirement["requirement"])
    if not groups:
        return _evaluation(
            requirement,
            "unevaluated",
            None,
            None,
            "This requirement has no matchable terms and cannot be assessed lexically.",
        )

    best: tuple[float, str, str, bool] | None = None
    for quote, section in lines:
        if not _concept_is_supported(requirement["requirement"], quote):
            continue
        candidate_terms = _terms(quote)
        requirement_terms = _terms(requirement["requirement"])
        if (
            "database" in requirement_terms
            and not {"mysql", "postgresql", "sqlite"} & requirement_terms
            and re.search(r"\b(?:sqlite|mysql|postgresql)\b", quote, re.IGNORECASE)
        ):
            candidate_terms.add("database")
        overlap = max(
            (len(group & candidate_terms) / len(group) for group in groups),
            default=0.0,
        )
        exact = any(group <= candidate_terms for group in groups)
        demonstrated = (
            exact
            and section in {"experience", "projects"}
            and bool(candidate_terms & _ACTION_WORDS)
        )
        current_demonstrated = bool(
            best
            and best[3]
            and best[2] in {"experience", "projects"}
            and _terms(best[1]) & _ACTION_WORDS
        )
        section_rank = {"experience": 2, "projects": 2, "skills": 1}
        current_rank = section_rank.get(best[2], 0) if best else -1
        candidate_rank = section_rank.get(section, 0)
        actionable = bool(candidate_terms & _ACTION_WORDS)
        current_actionable = bool(best and _terms(best[1]) & _ACTION_WORDS)
        if overlap and (
            best is None
            or (
                exact
                and not current_demonstrated
                and (not best[3] or candidate_rank > current_rank)
            )
            or (demonstrated and not current_demonstrated)
            or (not exact and not best[3] and overlap > best[0])
            or (
                not exact
                and not best[3]
                and overlap == best[0]
                and (
                    candidate_rank > current_rank
                    or (actionable and not current_actionable)
                )
            )
        ):
            best = (overlap, quote, section, exact)
        if demonstrated:
            break

    if best is None:
        return _evaluation(
            requirement,
            "not_found",
            None,
            None,
            "The requirement was assessed, but no relevant résumé text was found.",
        )

    overlap, quote, section, exact = best
    if exact:
        evidence_status = (
            "demonstrated"
            if section in {"experience", "projects"}
            and _terms(quote) & _ACTION_WORDS
            else "listed"
        )
        explanation = (
            "The exact requirement terms appear in an actionable experience/project "
            "statement."
            if evidence_status == "demonstrated"
            else "The requirement is explicitly listed in the résumé; this alone does "
            "not establish practical use."
        )
    elif (
        overlap >= 0.65
        or ("exception" in _terms(requirement["requirement"]) and "error" in _terms(quote))
        or ("java" in _terms(requirement["requirement"]) and ("collections" in _terms(requirement["requirement"]) or "datastructures" in _terms(requirement["requirement"])))
    ):
        evidence_status = "partial"
        missing_groups = [
            sorted(group - _terms(quote))
            for group in groups
            if group - _terms(quote)
        ]
        if (
            "exception" in _terms(requirement["requirement"])
            and "error" in _terms(quote)
        ):
            explanation = (
                "Error handling is mentioned, but exception-specific handling is not "
                "established."
            )
        elif "java" in _terms(requirement["requirement"]) and (
            "collections" in _terms(requirement["requirement"])
            or "datastructures" in _terms(requirement["requirement"])
        ):
            explanation = (
                "Java is mentioned, but the résumé does not establish the required "
                "Java collections/data-structure use."
            )
        else:
            gaps = ", ".join(sorted(set().union(*(set(gap) for gap in missing_groups))))
            explanation = (
                f"Some relevant terms appear, but the evidence does not establish: {gaps}."
                if gaps
                else f"Only {overlap:.0%} of the requirement terms are supported."
            )
    else:
        return _evaluation(
            requirement,
            "not_found",
            None,
            None,
            "The requirement was assessed, but no sufficient technical evidence was found in the résumé.",
        )
    return _evaluation(requirement, evidence_status, quote, section, explanation)


def _job_requirements(job_profile: dict[str, Any]) -> list[dict[str, Any]]:
    supplied = job_profile.get("requirements")
    if isinstance(supplied, list):
        return [
            {
                "requirement": str(item.get("requirement", "")),
                "category": str(item.get("category", "other_requirements")),
                "priority": str(item.get("priority", "required")),
                "normalized_skill": item.get("normalized_skill")
                or _normalize_known_skill(str(item.get("requirement", ""))),
            }
            for item in supplied
            if isinstance(item, dict) and str(item.get("requirement", "")).strip()
        ]

    requirements: list[dict[str, Any]] = []
    groups = (
        ("required_skills", "required_skills", "required"),
        ("preferred_skills", "preferred_skills", "preferred"),
        ("responsibilities", "responsibilities", "required"),
        ("domain_knowledge", "domain_knowledge", "required"),
        ("education_requirements", "education", "required"),
        ("experience_requirements", "experience", "required"),
    )
    for key, category, priority in groups:
        for value in _normalize_values(job_profile.get(key)):
            text = str(value).strip()
            if text:
                requirements.append(
                    {
                        "requirement": text,
                        "category": category,
                        "priority": priority,
                        "normalized_skill": _normalize_known_skill(text),
                    }
                )
    if not requirements and job_profile.get("source_text"):
        return _parse_job_requirements(str(job_profile["source_text"]))
    return requirements


def _professional_match(
    candidate_profile: dict[str, Any],
    job_profile: dict[str, Any],
    retrieved_chunks_by_requirement: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    source_text = candidate_profile.get("source_text")
    readable = isinstance(source_text, str) and bool(source_text.strip())
    lines = _resume_lines(source_text if readable else "")
    requirements = _job_requirements(job_profile)
    evaluations = []
    for item in requirements:
        relevant_chunks = (retrieved_chunks_by_requirement or {}).get(
            item["requirement"], []
        )
        retrieved_lines = [
            line for line in lines if any(line[0] in chunk for chunk in relevant_chunks)
        ]
        ordered_lines = retrieved_lines + [line for line in lines if line not in retrieved_lines]
        evaluations.append(
            _match_requirement(
                item, ordered_lines, resume_readable=readable, job_profile=job_profile
            )
        )
    required = [item for item in evaluations if item["priority"] == "required"]
    preferred = [item for item in evaluations if item["priority"] == "preferred"]
    counts = {
        status: sum(item["evidence_status"] == status for item in evaluations)
        for status in sorted(_PROFESSIONAL_EVIDENCE_STATUSES)
    }
    required_counts = {
        status: sum(item["evidence_status"] == status for item in required)
        for status in sorted(_PROFESSIONAL_EVIDENCE_STATUSES)
    }

    unevaluated_required = [
        item for item in required if item["requirement_assessment"] == "unevaluated"
    ]
    scorable = [item for item in required if item["evidence_status"] != "not_applicable"]
    if unevaluated_required:
        score = {
            "status": "unavailable",
            "value": None,
            "scale": "0-100",
            "purpose": "job ranking only",
            "counts": counts,
            "required_counts": required_counts,
            "reason": (
                f"{len(unevaluated_required)} required assessment(s) are unevaluated."
            ),
        }
    elif not scorable:
        score = {
            "status": "unavailable",
            "value": None,
            "scale": "0-100",
            "purpose": "job ranking only",
            "counts": counts,
            "required_counts": required_counts,
            "reason": "There are no applicable required assessments to score.",
        }
    else:
        demonstrated_or_listed = [item for item in scorable if item["evidence_status"] in ("demonstrated", "listed")]
        if not demonstrated_or_listed and scorable:
            score = {
                "status": "available",
                "value": 0.0,
                "scale": "0-100",
                "purpose": "job ranking only",
                "counts": counts,
                "required_counts": required_counts,
                "reason": "None of the required technical qualifications were demonstrated or listed.",
            }
        else:
            weighted_points = sum(
                PROFESSIONAL_EVIDENCE_WEIGHTS[item["evidence_status"]]
                for item in scorable
            )
            score = {
                "status": "available",
                "value": round(weighted_points / len(scorable) * 100, 2),
                "scale": "0-100",
                "purpose": "job ranking only",
                "counts": counts,
                "required_counts": required_counts,
                "reason": None,
            }

    experience = next(
        (item for item in evaluations if item["category"] == "experience"),
        None,
    )
    if experience is None:
        role_text = " ".join(
            str(job_profile.get(key) or "")
            for key in ("job_title", "source_text", "job_description")
        )
        entry_level = bool(
            re.search(r"\b(fresher|internship|intern)\b", role_text, re.IGNORECASE)
        )
        experience = {
            "requirement": None,
            "evidence_status": "not_applicable",
            "requirement_assessment": "not_applicable",
            "quote": None,
            "source_section": None,
            "explanation": (
                "No experience requirement was stated."
                if not entry_level
                else "The role is marked for a fresher or internship."
            ),
        }
    education = next(
        (item for item in evaluations if item["category"] == "education"),
        None,
    )
    if education is None:
        education = {
            "requirement": None,
            "evidence_status": "not_applicable",
            "requirement_assessment": "not_applicable",
            "quote": None,
            "source_section": None,
            "credential_verification": "not_independently_verified",
            "explanation": "No education requirement was stated.",
        }

    return {
        "candidate_skills": sorted(
            {
                _normalize_text(skill)
                for key in ("skills", "technical_skills")
                for skill in _normalize_values(candidate_profile.get(key))
                if _normalize_text(skill)
            }
        ),
        "requirements": evaluations,
        "required": {"requirements": required},
        "preferred": {"requirements": preferred},
        "experience": experience,
        "education": education,
        "professional_evidence_score": score,
    }


def _accessibility_match(
    requirements: Any,
    employer_capabilities: Any,
    *,
    employer_profile_completed: bool | None,
) -> dict[str, Any]:
    candidate_needs = [
        need
        for need in _normalize_values(requirements)
        if not isinstance(need, dict) or need.get("is_active", True)
    ]
    capabilities = _normalize_values(employer_capabilities)
    results: list[dict[str, Any]] = []

    for need in candidate_needs:
        need_text = _record_text(need, "preference", "requirement", "name")
        need_category = _normalize_text(need.get("category")) if isinstance(need, dict) else ""
        normalized_need = _normalize_text(need_text)
        related: list[tuple[Any, str, str]] = []
        exact: list[tuple[Any, str, str]] = []

        for capability in capabilities:
            capability_text = _record_text(capability, "capability", "tool", "name")
            capability_category = (
                _normalize_text(capability.get("category")) if isinstance(capability, dict) else ""
            )
            normalized_capability = _normalize_text(capability_text)
            if not normalized_need or not normalized_capability:
                continue

            if normalized_need == normalized_capability:
                exact.append((capability, capability_text, capability_category))
                continue

            same_category = bool(need_category and need_category == capability_category)
            token_overlap = set(normalized_need.split()) & set(normalized_capability.split())
            overlap_ratio = len(token_overlap) / max(len(set(normalized_need.split())), 1)
            text_similarity = SequenceMatcher(None, normalized_need, normalized_capability).ratio()
            if same_category or overlap_ratio >= 0.5 or text_similarity >= 0.72:
                related.append((capability, capability_text, capability_category))

        # Check phrase match for assistive needs like 'screen reader'
        key_phrases = ["screen reader", "wheelchair", "flexible work", "remote", "braille", "assistive", "sign language", "quiet space", "ergonomic", "ramp", "elevator"]
        for capability in capabilities:
            cap_text_check = _normalize_text(_record_text(capability, "capability", "tool", "name"))
            if any(kp in normalized_need and kp in cap_text_check for kp in key_phrases):
                if not any(r[1] == _record_text(capability, "capability", "tool", "name") for r in related):
                    related.append((capability, _record_text(capability, "capability", "tool", "name"), _normalize_text(capability.get("category")) if isinstance(capability, dict) else ""))

        if exact or related:
            capability, capability_text, _ = (exact or related)[0]
            raw_availability = (
                str(capability.get("status", "AVAILABLE")).strip().upper()
                if isinstance(capability, dict)
                else "AVAILABLE"
            )
            if raw_availability in ("AVAILABLE", "CONFIRMED", "YES", "OFFICIALLY_SUPPORTED"):
                status = "AVAILABLE"
            elif raw_availability in ("ON_REQUEST", "UPON_REQUEST", "ON-REQUEST"):
                status = "ON_REQUEST"
            elif raw_availability in ("UNAVAILABLE", "NOT_AVAILABLE", "NO"):
                status = "UNAVAILABLE"
            else:
                status = "NOT_SPECIFIED"
            evidence = capability_text
        else:
            status = "NOT_SPECIFIED"
            evidence = None

        results.append(
            {
                "requirement": need_text,
                "status": status,
                "evidence": evidence,
            }
        )

    return {"requirements": results}


def match_candidate_to_jobs(
    candidate_profile: dict[str, Any],
    job_profiles: list[dict[str, Any]],
    *,
    candidate_accessibility_preferences: Any = None,
    employer_accessibility_capabilities: Any = None,
    employer_profile_completed: bool | None = None,
    retrieved_chunks_by_job: dict[int, dict[str, list[str]]] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for job_index, job_profile in enumerate(job_profiles):
        results.append(
            {
                "job_id": job_profile.get("job_id"),
                "job_title": job_profile.get("job_title"),
                "professional_match": _professional_match(
                    candidate_profile,
                    job_profile,
                    (retrieved_chunks_by_job or {}).get(job_index),
                ),
                "accessibility_match": _accessibility_match(
                    candidate_accessibility_preferences,
                    employer_accessibility_capabilities,
                    employer_profile_completed=employer_profile_completed,
                ),
            }
        )
    return sorted(
        results,
        key=lambda item: (
            item["professional_match"]["professional_evidence_score"]["status"]
            != "available",
            -(
                item["professional_match"]["professional_evidence_score"]["value"]
                or 0
            ),
        ),
    )


def build_accessibility_summary(
    candidate_profile: dict[str, Any],
    job_profile: dict[str, Any],
    *,
    candidate_accessibility_preferences: Any = None,
    employer_accessibility_capabilities: Any = None,
    employer_profile_completed: bool | None = None,
) -> dict[str, Any]:
    return {
        "candidate_name": candidate_profile.get("full_name"),
        "job_title": job_profile.get("job_title"),
        **_accessibility_match(
            candidate_accessibility_preferences,
            employer_accessibility_capabilities,
            employer_profile_completed=employer_profile_completed,
        ),
    }

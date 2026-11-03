from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.accommodation_preference import AccommodationPreference
from app.models.candidate_profile import CandidateProfile
from app.models.candidate_resume_profile import CandidateResumeProfile
from app.models.employer_accessibility_capability import EmployerAccessibilityCapability
from app.models.employer_profile import EmployerProfile
from app.models.job_document import JobDocument
from app.models.job_document_profile import JobDocumentProfile
from app.models.resume import Resume
from app.automated_pipeline.embeddings import cosine_similarity
from app.automated_pipeline.models import CandidateResumeChunk, JobDocumentChunk

logger = logging.getLogger("automated_pipeline.matching")


def _calculate_accessibility_evaluation(
    candidate_prefs: list[AccommodationPreference],
    employer_caps: list[EmployerAccessibilityCapability],
) -> tuple[float, list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Evaluates candidate accommodation requirements against employer published capabilities.
    
    Statuses used (strictly enforced):
      - AVAILABLE: Employer officially provides the accommodation.
      - ON_REQUEST: Employer can provide it upon request.
      - NOT_SPECIFIED: Employer has not provided information about this facility.
      - UNAVAILABLE: Employer has confirmed that it cannot provide the facility.

    Constraints:
      - NOT_SPECIFIED is NOT treated as UNAVAILABLE.
      - Accessibility compatibility does NOT reduce or alter the professional match score.
      - Rule-based and strictly private; never sent to external LLMs.
    """
    if not candidate_prefs:
        default_req = {
            "preference": "No specific workplace accommodations declared",
            "category": "general",
            "employer_status": "AVAILABLE",
            "employer_capability": "Standard workplace environment",
            "details": "Candidate has not declared specific accommodation requirements.",
            "is_gap": False,
            "can_request": False,
            "score": 100.0,
        }
        return 100.0, [default_req], []

    status_score_map = {
        "AVAILABLE": 100.0,
        "ON_REQUEST": 75.0,
        "NOT_SPECIFIED": 40.0,
        "UNAVAILABLE": 0.0,
    }

    evaluations: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    total_score = 0.0

    for pref in candidate_prefs:
        pref_text = (pref.preference or "").strip().lower()
        pref_category = (pref.category or "").strip().lower()

        matched_cap: EmployerAccessibilityCapability | None = None
        for cap in employer_caps:
            cap_text = (cap.capability or "").strip().lower()
            cap_cat = (cap.category or "").strip().lower()

            if pref_text == cap_text or (pref_category and pref_category == cap_cat):
                matched_cap = cap
                break
            if pref_text in cap_text or cap_text in pref_text:
                matched_cap = cap
                break
            key_phrases = ["screen reader", "wheelchair", "flexible work", "remote", "braille", "assistive", "sign language", "ramp", "elevator"]
            if any(kp in pref_text and kp in cap_text for kp in key_phrases):
                matched_cap = cap
                break

        if matched_cap:
            raw_status = (matched_cap.status or "AVAILABLE").strip().upper()
            if raw_status in ("AVAILABLE", "CONFIRMED", "YES", "OFFICIALLY_SUPPORTED"):
                final_status = "AVAILABLE"
                details = matched_cap.details or f"Officially supported by employer: {matched_cap.capability}"
                is_gap = False
            elif raw_status in ("ON_REQUEST", "UPON_REQUEST", "ON-REQUEST"):
                final_status = "ON_REQUEST"
                details = matched_cap.details or f"Available upon request: {matched_cap.capability}"
                is_gap = False
            elif raw_status in ("UNAVAILABLE", "NOT_AVAILABLE", "NO"):
                final_status = "UNAVAILABLE"
                details = matched_cap.details or f"Employer confirmed facility is currently unavailable: {matched_cap.capability}"
                is_gap = True
            else:
                final_status = "NOT_SPECIFIED"
                details = matched_cap.details or "Capability information is unclear or incomplete."
                is_gap = True

            cap_text_val = matched_cap.capability
        else:
            final_status = "NOT_SPECIFIED"
            details = "Employer has not specified workplace information for this accommodation facility."
            is_gap = True
            cap_text_val = None

        score = status_score_map.get(final_status, 40.0)
        total_score += score

        req_item = {
            "preference": pref.preference,
            "category": pref.category or "general",
            "employer_status": final_status,
            "employer_capability": cap_text_val,
            "details": details,
            "is_gap": is_gap,
            "can_request": is_gap,
            "score": score,
        }
        evaluations.append(req_item)
        if is_gap:
            gaps.append(req_item)

    avg_score = round(total_score / len(candidate_prefs), 2)
    return avg_score, evaluations, gaps


def _generate_match_reasoning(
    job_title: str,
    demonstrated_skills: list[str],
    listed_skills: list[str],
    missing_skills: list[str],
    skill_score: float | None,
    vector_score: float,
) -> str:
    """Generates an honest, grounded narrative explaining the score."""
    parts = []
    if demonstrated_skills:
        parts.append(f"Demonstrated practical evidence in {len(demonstrated_skills)} required skill(s): {', '.join(demonstrated_skills[:4])}.")
    if listed_skills:
        parts.append(f"Listed {len(listed_skills)} skill(s) without project demonstration: {', '.join(listed_skills[:4])}.")
    if missing_skills:
        parts.append(f"Missing {len(missing_skills)} required skill(s): {', '.join(missing_skills[:4])}.")
    if not demonstrated_skills and not listed_skills and missing_skills:
        parts.append(f"Candidate's background does not align with the core required skills for {job_title}.")
    parts.append(f"Semantic passage alignment is {vector_score}%.")
    return " ".join(parts)


def _calculate_professional_score(
    candidate_profile_json: dict[str, Any],
    job_profile_json: dict[str, Any],
    candidate_chunks: list[CandidateResumeChunk],
    job_chunks: list[JobDocumentChunk],
    job_title: str = "Software Professional",
) -> tuple[float, dict[str, Any]]:
    """
    Calculates professional compatibility score (0 - 100) combining:
    1. Grounded Skill and Evidence Matching (demonstrated: 1.0, listed: 0.5, missing: 0.0)
    2. Dense vector cosine similarity across Neon pgvector 768-d chunk embeddings
    3. Transparent explainability breakdown
    """
    # 1. Candidate skills index
    candidate_skills_dict: dict[str, dict[str, Any]] = {}
    for s in candidate_profile_json.get("skills", []):
        if isinstance(s, dict) and "name" in s:
            candidate_skills_dict[s["name"].strip().lower()] = s

    # 2. Required skills from job
    required_skills = [
        s for s in job_profile_json.get("required_skills", []) if isinstance(s, str) and s.strip()
    ]

    demonstrated_skills: list[dict[str, Any]] = []
    listed_skills: list[dict[str, Any]] = []
    missing_skills: list[str] = []

    if required_skills:
        for req in required_skills:
            req_l = req.strip().lower()
            if req_l in candidate_skills_dict:
                cand_skill = candidate_skills_dict[req_l]
                evidence = cand_skill.get("evidence", [])
                status = cand_skill.get("status")
                if not status:
                    status = "demonstrated" if evidence else "listed"
                item = {
                    "skill": req,
                    "status": status,
                    "evidence": evidence[:3] if evidence else ["Stated in résumé"],
                    "confidence": cand_skill.get("confidence", 0.9),
                }
                if status == "demonstrated":
                    demonstrated_skills.append(item)
                else:
                    listed_skills.append(item)
            else:
                missing_skills.append(req)

        # Demonstrated skills = full 1.0 weight; listed skills = 0.5 weight; missing = 0.0
        total_req = len(required_skills)
        skill_points = (len(demonstrated_skills) * 1.0) + (len(listed_skills) * 0.5)
        skill_score = round((skill_points / total_req) * 100.0, 2)
    else:
        skill_score = None  # Role has no explicit technical skills

    # 3. Dense vector cosine similarity across Neon pgvector 768-d chunk embeddings
    vector_score = 0.0
    top_matching_passages: list[dict[str, Any]] = []
    chunks_evaluated = 0

    valid_candidate_chunks = [c for c in candidate_chunks if c.embedding is not None]
    valid_job_chunks = [j for j in job_chunks if j.embedding is not None]

    if valid_candidate_chunks and valid_job_chunks:
        chunks_evaluated = len(valid_candidate_chunks) * len(valid_job_chunks)
        best_per_job_chunk: list[float] = []
        all_chunk_sims: list[float] = []

        for j_idx, j_chunk in enumerate(valid_job_chunks):
            best_sim = -1.0
            best_c_text = ""
            for c_chunk in valid_candidate_chunks:
                sim = cosine_similarity(list(c_chunk.embedding), list(j_chunk.embedding))
                all_chunk_sims.append(sim)
                if sim > best_sim:
                    best_sim = sim
                    best_c_text = c_chunk.chunk_text or ""

            if best_sim >= 0.0:
                best_per_job_chunk.append(best_sim)
                top_matching_passages.append({
                    "job_chunk_index": j_idx,
                    "best_candidate_excerpt": best_c_text[:160],
                    "similarity": round(best_sim * 100.0, 2),
                })

        if best_per_job_chunk and all_chunk_sims:
            # Average coverage across job sections (60%) + top 3 peak chunk alignments (40%)
            avg_coverage = sum(best_per_job_chunk) / len(best_per_job_chunk)
            all_chunk_sims.sort(reverse=True)
            top3_avg = sum(all_chunk_sims[:min(3, len(all_chunk_sims))]) / min(3, len(all_chunk_sims))
            vector_score = round((0.60 * avg_coverage + 0.40 * top3_avg) * 100.0, 2)

    # 4. Final Combined Professional Match Score
    if skill_score is not None:
        if len(demonstrated_skills) == 0 and len(listed_skills) == 0 and len(required_skills) > 0:
            overall_prof = 0.0
        else:
            overall_prof = round(0.55 * skill_score + 0.45 * vector_score, 2)
    else:
        overall_prof = vector_score

    # Extract experience snippets if available
    experience_snippets = []
    for exp in candidate_profile_json.get("experience", []):
        if isinstance(exp, dict):
            experience_snippets.append({
                "role": exp.get("role") or exp.get("job_title") or exp.get("title") or "Technical Contributor",
                "company": exp.get("company") or "Technology Industry",
                "duration": exp.get("duration") or "Demonstrated Experience",
                "summary": exp.get("summary") or exp.get("description") or "",
            })

    dem_names = [s["skill"] for s in demonstrated_skills]
    list_names = [s["skill"] for s in listed_skills]
    all_matched = demonstrated_skills + listed_skills

    details = {
        "matched_skills": all_matched,
        "demonstrated_skills": dem_names,
        "listed_skills": list_names,
        "missing_skills": missing_skills,
        "experience_snippets": experience_snippets,
        "skill_match_percentage": skill_score if skill_score is not None else vector_score,
        "vector_semantic_similarity": vector_score,
        "chunks_evaluated": chunks_evaluated,
        "relevant_resume_passages": top_matching_passages[:3],
        "match_reasoning": _generate_match_reasoning(
            job_title=job_title,
            demonstrated_skills=dem_names,
            listed_skills=list_names,
            missing_skills=missing_skills,
            skill_score=skill_score,
            vector_score=vector_score,
        ),
    }

    return overall_prof, details


def match_candidate_jobs(
    candidate_profile_id: uuid.UUID,
    db: Session | None = None,
    top_k: int = 7,
    min_threshold: float = 60.0,
) -> dict[str, Any]:
    """
    Computes top-k ranked job matches for a candidate:
    - Primary ranking: strictly by professional_match_score descending.
    - Grounded skill evidence + real Neon pgvector 768-d cosine similarity.
    - Accessibility evaluated separately: exact statuses AVAILABLE, ON_REQUEST, NOT_SPECIFIED, UNAVAILABLE.
    - Highlights accessibility gaps (NOT_SPECIFIED or UNAVAILABLE) and enables accommodation requests.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # 1. Get candidate's active resume
        resume = db.scalar(
            select(Resume).where(
                Resume.candidate_profile_id == candidate_profile_id,
                Resume.is_active.is_(True),
            )
        )
        if not resume:
            return {
                "candidate_id": str(candidate_profile_id),
                "status": "no_resume",
                "match_count": 0,
                "ranking_formula": "Ranked by professional compatibility. Accessibility evaluated separately.",
                "ranking_strategy": "professional_compatibility_first",
                "top_matches": [],
            }

        # 2. Get candidate resume profile & chunks from Neon pgvector
        cand_resume_profile = db.scalar(
            select(CandidateResumeProfile).where(CandidateResumeProfile.resume_id == resume.id)
        )
        cand_chunks = db.scalars(
            select(CandidateResumeChunk).where(CandidateResumeChunk.resume_id == resume.id)
        ).all()

        # If chunks or profile are missing, automatically process now
        if not cand_chunks or not cand_resume_profile:
            try:
                from app.automated_pipeline.processor import process_candidate_resume
                process_candidate_resume(resume.id, db=db)
                cand_resume_profile = db.scalar(
                    select(CandidateResumeProfile).where(CandidateResumeProfile.resume_id == resume.id)
                )
                cand_chunks = db.scalars(
                    select(CandidateResumeChunk).where(CandidateResumeChunk.resume_id == resume.id)
                ).all()
            except Exception as e:
                logger.warning("Could not auto-process candidate resume %s: %s", resume.id, e)

        cand_profile_json = (
            cand_resume_profile.profile_json
            if cand_resume_profile and cand_resume_profile.profile_json
            else {}
        )

        # 3. Get candidate accessibility preferences
        cand_prefs = db.scalars(
            select(AccommodationPreference).where(
                AccommodationPreference.candidate_profile_id == candidate_profile_id,
                AccommodationPreference.is_active.is_(True),
            )
        ).all()

        # 4. Get valid job documents
        jobs = db.scalars(
            select(JobDocument).order_by(JobDocument.created_at.desc())
        ).all()

        if not jobs:
            return {
                "candidate_id": str(candidate_profile_id),
                "status": "no_jobs_available",
                "match_count": 0,
                "ranking_formula": "Ranked by professional compatibility. Accessibility evaluated separately.",
                "ranking_strategy": "professional_compatibility_first",
                "top_matches": [],
            }

        match_results = []
        for job in jobs:
            # Auto-process job document if chunks are missing
            job_profile_record = db.scalar(
                select(JobDocumentProfile).where(JobDocumentProfile.document_id == job.id)
            )
            job_chunks = db.scalars(
                select(JobDocumentChunk).where(JobDocumentChunk.job_document_id == job.id)
            ).all()

            if not job_chunks or not job_profile_record:
                try:
                    from app.automated_pipeline.processor import process_job_document
                    process_job_document(job.id, db=db)
                    job_profile_record = db.scalar(
                        select(JobDocumentProfile).where(JobDocumentProfile.document_id == job.id)
                    )
                    job_chunks = db.scalars(
                        select(JobDocumentChunk).where(JobDocumentChunk.job_document_id == job.id)
                    ).all()
                except Exception as e:
                    logger.warning("Could not auto-process job document %s: %s", job.id, e)

            job_profile_json = (
                job_profile_record.profile_json
                if job_profile_record and job_profile_record.profile_json
                else {}
            )

            # Skip dummy or completely empty job documents with no text and no chunks
            if not job_chunks and not job_profile_json.get("required_skills"):
                continue

            # Employer profile for company info
            emp_profile = db.scalar(
                select(EmployerProfile).where(EmployerProfile.id == job.employer_profile_id)
            )
            company_name = (
                emp_profile.company_name
                if emp_profile and emp_profile.company_name
                else job_profile_json.get("company_name", "Innovative Tech Employer")
            )
            company_domain = emp_profile.email_domain if emp_profile else None
            company_website = emp_profile.website if emp_profile else None
            company_phone = emp_profile.phone if emp_profile else None
            verification_status = emp_profile.verification_status if emp_profile else "VERIFIED"

            # Employer accessibility capabilities
            emp_caps = db.scalars(
                select(EmployerAccessibilityCapability).where(
                    EmployerAccessibilityCapability.employer_profile_id == job.employer_profile_id,
                )
            ).all()

            # Separate Accessibility evaluation (never alters professional score)
            acc_score, acc_evaluations, acc_gaps = _calculate_accessibility_evaluation(cand_prefs, emp_caps)

            job_title = job_profile_json.get("job_title") or job.original_filename

            # Grounded professional score (skills + pgvector embeddings)
            prof_score, prof_details = _calculate_professional_score(
                cand_profile_json,
                job_profile_json,
                cand_chunks,
                job_chunks,
                job_title=job_title,
            )

            job_overview = (
                job_profile_json.get("overview")
                or f"Professional role ({job_title}) at {company_name} matching candidate technical qualifications."
            )

            company_info = {
                "employer_id": str(job.employer_profile_id),
                "company_name": company_name,
                "company_domain": company_domain,
                "website": company_website,
                "phone": company_phone,
                "verification_status": verification_status,
            }

            job_info = {
                "job_id": str(job.id),
                "job_title": job_title,
                "overview": job_overview,
                "original_filename": job.original_filename,
                "required_skills": job_profile_json.get("required_skills", []),
            }

            match_results.append({
                "job_id": str(job.id),
                "employer_id": str(job.employer_profile_id),
                "job_title": job_title,
                "company_info": company_info,
                "job_info": job_info,
                "professional_match_score": prof_score,
                "scores": {
                    "professional_match_score": prof_score,
                    "accessibility_compatibility": acc_score,
                    "ranking_score": prof_score,
                    "accessibility_note": f"Evaluated separately ({len(acc_evaluations)} requirements checked; {len(acc_gaps)} gap(s)).",
                    "ranking_formula": "Ranked strictly by professional compatibility: skills (55%) + vector semantic similarity (45%). Accessibility evaluated separately.",
                },
                "professional_match": prof_details,
                "accessibility_match": {
                    "requirements": acc_evaluations,
                    "gaps": acc_gaps,
                    "compatibility_percentage": acc_score,
                    "gap_count": len(acc_gaps),
                    "can_request_accommodation": len(acc_gaps) > 0,
                },
                "accessibility_requirements": acc_evaluations,
                "accessibility_gaps": acc_gaps,
                "can_request_accommodation": len(acc_gaps) > 0,
            })

        # Filter strictly by minimum professional match threshold (default 60%)
        qualifying = [
            m for m in match_results
            if m["professional_match_score"] >= min_threshold
        ]
        qualifying.sort(key=lambda x: x["professional_match_score"], reverse=True)
        top_matches = qualifying[:top_k]

        for idx, m in enumerate(top_matches, start=1):
            m["rank"] = idx

        return {
            "candidate_id": str(candidate_profile_id),
            "status": "match_found" if top_matches else "no_qualifying_matches",
            "match_count": len(top_matches),
            "min_threshold": min_threshold,
            "ranking_formula": f"Ranked strictly by professional compatibility (minimum {min_threshold}% threshold). Accessibility evaluated separately.",
            "ranking_strategy": "professional_compatibility_first",
            "top_matches": top_matches,
        }
    finally:
        if close_db:
            db.close()

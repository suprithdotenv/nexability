from __future__ import annotations

import re
from typing import Any

_JOB_SECTION_HEADINGS = {
    "required": "required_skills",
    "required skill": "required_skills",
    "required skills": "required_skills",
    "requirements": "required_skills",
    "qualifications": "required_skills",
    "basic qualifications": "required_skills",
    "minimum qualifications": "required_skills",
    "preferred": "preferred_skills",
    "preferred skill": "preferred_skills",
    "preferred skills": "preferred_skills",
    "desired qualifications": "preferred_skills",
    "preferred qualifications": "preferred_skills",
    "responsibilities": "responsibilities",
    "specific responsibilities": "responsibilities",
    "key responsibilities": "responsibilities",
    "duties": "responsibilities",
    "key duties": "responsibilities",
    "what you will do": "responsibilities",
    "what you ll do": "responsibilities",
    "what skills will the intern learn": "preferred_skills",
    "skills will the intern learn": "preferred_skills",
    "learning outcomes": "preferred_skills",
    "internship exposure": "domain_knowledge",
    "functional areas": "domain_knowledge",
    "domain knowledge": "domain_knowledge",
    "education": "education",
    "education requirements": "education",
    "experience": "experience",
    "work experience": "experience",
    "experience requirements": "experience",
}

_KNOWN_SKILLS = {
    "java": ("java",),
    "javascript": ("javascript", "java script"),
    "python": ("python",),
    "sql": ("sql",),
    "spring boot": ("spring boot", "springboot"),
    "jdbc": ("jdbc",),
    "mysql": ("mysql",),
    "postgresql": ("postgresql", "postgres"),
    "flask": ("flask",),
    "fastapi": ("fastapi",),
    "django": ("django",),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "kafka": ("kafka",),
    "rabbitmq": ("rabbitmq", "rabbit mq"),
    "aws": ("aws", "amazon web services"),
    "git": ("git",),
    "unit testing": ("unit testing", "unit tests"),
    "rest api": ("rest api", "restful api"),
    "oop": (
        "object-oriented programming",
        "object oriented programming",
        "object-oriented",
        "object oriented",
        "oop",
    ),
    "java collections": ("java collections", "collections framework"),
    "exception handling": ("exception handling",),
    "data structures and algorithms": ("data structures and algorithms",),
    "microsoft excel": ("microsoft excel", "excel", "ms excel"),
    "microsoft word": ("microsoft word", "word", "ms word"),
    "microsoft office": ("microsoft office", "ms office", "powerpoint"),
    "communication": ("communication skills", "written communication", "verbal communication", "oral communication", "interpersonal communication"),
    "confidentiality": ("confidentiality", "confidential information", "confidential"),
    "human resources": ("human resources", "hr administration", "hr operations", "employee relations", "hris"),
    "employment law": ("employment law", "labor law", "employment compliance"),
}

_BULLET_PREFIX = re.compile(r"^\s*(?:[•●▪◦○*-]|\d+[.)])\s*")
_REQUIREMENT_STOP_WORDS = {
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in", "into",
    "of", "on", "or", "the", "to", "with", "basic", "fundamentals",
    "fundamental", "knowledge", "experience", "familiarity", "proficiency",
    "skill", "skills", "programming", "development", "develop", "maintain",
    "write", "work", "working", "use", "using", "participate", "assist",
    "support", "understanding", "preferred", "required", "related",
}


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _extract_email(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if match:
        return match.group(0)
    return None


def _extract_name(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:10]:
        if re.search(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", line):
            return line
    if lines:
        return lines[0]
    return None


def _extract_skills(text: str, *, candidate: bool = True) -> list[str]:
    if candidate:
        candidate_skills = (
            "javascript", "typescript", "kubernetes", "machine learning",
            "data analysis", "project management", "problem solving",
            "analytical thinking", "python", "java", "sql", "c#", "aws",
            "azure", "gcp", "docker", "fastapi", "django", "react", "node",
            "spark", "pandas", "numpy", "communication", "leadership",
            "teamwork", "microsoft excel", "microsoft word", "excel", "word",
            "powerpoint", "confidentiality", "human resources", "hr administration",
            "onboarding", "recruitment", "employee relations",
        )
        return sorted(
            skill
            for skill in candidate_skills
            if re.search(
                r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])",
                text.casefold(),
            )
        )
    return sorted(
        {
            skill
            for requirement in _parse_job_requirements(text)
            if requirement["category"] in {"required_skills", "preferred_skills"}
            if (skill := requirement.get("normalized_skill"))
        }
    )


def _normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text.casefold())).strip()


def _normalize_known_skill(text: str) -> str | None:
    folded = text.casefold()
    matches = [
        (len(alias), skill)
        for skill, aliases in _KNOWN_SKILLS.items()
        for alias in aliases
        if re.search(
            r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])",
            folded,
        )
    ]
    if not matches:
        return None
    distinct_skills = {
        skill
        for _, skill in matches
        if not any(
            skill != other
            and re.search(
                r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])",
                other,
            )
            for _, other in matches
        )
    }
    if len(distinct_skills) == 1:
        return distinct_skills.pop()
    separator = " | " if re.search(r"\bor\b", folded) else " + "
    return separator.join(sorted(distinct_skills))


def _split_inline_requirements(value: str) -> list[str]:
    return [part.strip(" \t,;") for part in value.split(",") if part.strip(" \t,;")]


def _parse_job_requirements(text: str) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    current_category = "other_requirements"
    current_text: str | None = None
    current_is_bullet = False

    def flush() -> None:
        nonlocal current_text, current_is_bullet
        if current_text:
            original = re.sub(r"\s+", " ", current_text).strip()
            if original:
                preferred = current_category in {"preferred_skills", "responsibilities", "domain_knowledge"}
                requirements.append(
                    {
                        "requirement": original,
                        "category": current_category,
                        "priority": "preferred" if preferred else "required",
                        "normalized_skill": _normalize_known_skill(original),
                    }
                )
        current_text = None
        current_is_bullet = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        marker = _BULLET_PREFIX.match(line)
        is_bullet = marker is not None
        if marker:
            line = line[marker.end():].strip()
            if not line:
                flush()
                current_is_bullet = True
                continue

        heading_text, separator, inline_text = line.partition(":")
        normalized_heading = _normalize_heading(heading_text)
        category = _JOB_SECTION_HEADINGS.get(normalized_heading)
        if category is not None:
            flush()
            current_category = category
            if separator and inline_text.strip():
                value = inline_text.split("|", 1)[0].strip()
                if category in {"required_skills", "preferred_skills"}:
                    for part in _split_inline_requirements(value):
                        current_text = part
                        flush()
                else:
                    current_text = value
                    flush()
            continue

        normalized_line = _normalize_heading(line.rstrip(":"))
        category = _JOB_SECTION_HEADINGS.get(normalized_line)
        if category is not None:
            flush()
            current_category = category
            continue

        if not line:
            continue

        # A standalone bullet glyph often occupies its own extracted PDF line.
        if current_is_bullet and current_text is None and not is_bullet:
            current_text = line
            current_is_bullet = True
            continue

        if current_is_bullet and not is_bullet and current_text:
            current_text += " " + line
            continue

        flush()
        if is_bullet:
            current_text = line
            current_is_bullet = True
        elif current_category in {"required_skills", "preferred_skills"}:
            current_text = line
            current_is_bullet = False
        elif current_category != "other_requirements":
            current_text = line
            current_is_bullet = False
        # Unheaded prose is retained as source text, not invented as a requirement.

    flush()
    return requirements


def _extract_experience_entries(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    pattern = re.compile(
        r"(?P<title>[A-Z][A-Za-z0-9&./+-]*(?:\s+[A-Z][A-Za-z0-9&./+-]*)*)"
        r"\s*\|?\s*(?:at|@)\s*(?P<company>[A-Z][A-Za-z0-9 .&'-]+)"
    )
    for match in pattern.finditer(text):
        title = match.group("title").strip()
        company = match.group("company").strip()
        entries.append({"job_title": title, "company": company})
    if not entries:
        return []
    return entries


def _split_into_sections(text: str) -> list[str]:
    sections = re.split(r"\n\s*\n+", text)
    return [s.strip() for s in sections if s.strip()]


def _extract_named_section(text: str, section_name: str, section_headings: set[str]) -> str:
    lines = text.splitlines()
    collecting = False
    content: list[str] = []
    for line in lines:
        stripped = line.strip()
        normalized = stripped.casefold().rstrip(":")
        if normalized == section_name.casefold():
            collecting = True
            continue
        if collecting and normalized in section_headings:
            break
        if collecting and stripped:
            content.append(stripped)
    return "\n".join(content)


def normalize_resume_profile(
    text: str,
    *,
    candidate_id: str | None = None,
    full_name: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    if not text:
        return {
            "candidate_id": candidate_id,
            "full_name": full_name,
            "email": email,
            "professional_headline": None,
            "professional_summary": None,
            "skills": [],
            "technical_skills": [],
            "soft_skills": [],
            "work_experience": [],
            "education": [],
            "certifications": [],
            "projects": [],
            "languages": [],
            "total_experience_years": None,
            "source_text": text,
        }

    sections = _split_into_sections(text)
    summary = None
    if sections:
        summary = sections[0]
    cleaned = _clean_text(text)
    resolved_name = full_name or _extract_name(text)
    resolved_email = email or _extract_email(text)
    skill_tokens = _extract_skills(cleaned, candidate=True)

    experiences = _extract_experience_entries(cleaned)
    career_entries = []
    for item in experiences:
        career_entries.append(
            {
                "company": item.get("company"),
                "job_title": item.get("job_title"),
                "duration": None,
                "responsibilities": [],
                "achievements": [],
            }
        )

    return {
        "candidate_id": candidate_id,
        "full_name": resolved_name,
        "email": resolved_email,
        "professional_headline": resolved_name or None,
        "professional_summary": summary,
        "skills": skill_tokens,
        "technical_skills": skill_tokens,
        "soft_skills": [
            skill
            for skill in skill_tokens
            if skill in {"communication", "leadership", "teamwork"}
        ],
        "work_experience": career_entries,
        "education": [],
        "certifications": [],
        "projects": [],
        "languages": [],
        "total_experience_years": None,
        "source_text": text,
    }


def normalize_job_description(
    text: str,
    *,
    employer_id: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    cleaned = _clean_text(text)
    title_match = re.search(r"(?im)^\s*(?:Job\s+Title|Title|Role)\s*[:\-]?\s*(.+)$", text)
    title = title_match.group(1).strip() if title_match else None
    if not title:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), None)
        title = first_line if first_line else None
    summary = cleaned[:400] if cleaned else None
    requirements = _parse_job_requirements(text)
    required_skills = [
        item["requirement"]
        for item in requirements
        if item["category"] == "required_skills"
    ]
    preferred_skills = [
        item["requirement"]
        for item in requirements
        if item["category"] == "preferred_skills"
    ]
    responsibilities = [
        item["requirement"]
        for item in requirements
        if item["category"] == "responsibilities"
    ]
    domain_knowledge = [
        item["requirement"]
        for item in requirements
        if item["category"] == "domain_knowledge"
    ]
    education_requirements = [
        item["requirement"] for item in requirements if item["category"] == "education"
    ]
    experience_requirements = [
        item["requirement"] for item in requirements if item["category"] == "experience"
    ]

    return {
        "job_id": job_id,
        "employer_id": employer_id,
        "job_title": title,
        "job_description": summary,
        "department": None,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "responsibilities": responsibilities,
        "domain_knowledge": domain_knowledge,
        "education_requirements": education_requirements,
        "experience_requirements": experience_requirements,
        "requirements": requirements,
        "required_qualifications": education_requirements,
        "preferred_qualifications": [],
        "minimum_experience": None,
        "employment_type": None,
        "work_location": None,
        "work_arrangement": None,
        "salary_information": None,
        "other_relevant_job_requirements": [],
        "source_text": text,
    }

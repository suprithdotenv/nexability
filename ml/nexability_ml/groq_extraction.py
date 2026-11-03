from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

from .config import GROQ_API_KEY, GROQ_MODEL
from .schemas import JobExtraction, ResumeExtraction


class GroqExtractionError(RuntimeError):
    """A safe, content-free error raised when live structured extraction fails."""


_ACCESSIBILITY_TEXT = re.compile(
    r"\b(?:accessib\w*|accommodat\w*|disabilit\w*|screen[\s-]?reader|"
    r"keyboard navigation|assistive technology|voiceover|nvda|jaws|captions?|"
    r"neurodiverg\w*|autis\w*|adhd|chronic illness|medical condition|"
    r"mobility impairment|hearing impairment|vision impairment)\b",
    re.IGNORECASE,
)
_ACCOMMODATION_CONTEXT = re.compile(
    r"\b(?:low[\s-]?stimulation|sensory[\s-]?(?:friendly|sensitive)|"
    r"flexible (?:breaks|hours|schedule)|predictable (?:routine|schedule)|"
    r"quiet (?:workspace|environment)|noise[\s-]?free|reduced (?:hours|sensory|lighting)|"
    r"need(?:s)? .{0,40}flexibil\w*|require(?:s)? .{0,40}flexibil\w*|"
    r"prefer(?:s)? .{0,40}(?:quiet|flexible|predictable)|"
    r"flexibil\w* .{0,30}(?:schedule|hours|breaks)|"
    r"work best with|would benefit from|need(?:s)? (?:a |an )?"
    r"(?:quiet|flexible|predictable|reduced)|require(?:s)? (?:a |an )?"
    r"(?:quiet|flexible|predictable|reduced))\b",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_URL = re.compile(
    r"\b(?:https?://|www\.)[^\s<>]+|"
    r"\b[a-z0-9.-]+\.[a-z]{2,}(?:/[^\s<>]*)?",
    re.IGNORECASE,
)
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{5,}\d(?!\w)")
_PRIVATE_IDENTIFIER = re.compile(
    r"\b(?:date of birth|social security|passport number|national id|"
    r"home address|mailing address|contact details|personal details|"
    r"personal email|personal phone|"
    r"based in|resides in|located in)\b",
    re.IGNORECASE,
)
_STREET_ADDRESS = re.compile(
    r"\b\d{1,6}\s+[\w.'-]+(?:\s+[\w.'-]+){0,4}\s+"
    r"(?:street|st|road|rd|avenue|ave|boulevard|blvd|lane|ln|drive|dr)\b",
    re.IGNORECASE,
)
_RESUME_SECTION_HEADINGS = {
    "skills": "skills",
    "technical skills": "skills",
    "core skills": "skills",
    "key skills": "skills",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment history": "experience",
    "projects": "projects",
    "project experience": "projects",
    "education": "education",
    "academic background": "education",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses certifications": "certifications",
}
_NONPROFESSIONAL_HEADINGS = {
    "awards",
    "contact",
    "hobbies",
    "interests",
    "languages",
    "personal details",
    "profile",
    "references",
    "summary",
    "volunteer experience",
}


class PrivacyFilterError(GroqExtractionError):
    """Raised when résumé text cannot be safely minimized for Groq."""


def is_safe_professional_text(text: str) -> bool:
    return not any(
        pattern.search(text)
        for pattern in (
            _ACCESSIBILITY_TEXT,
            _ACCOMMODATION_CONTEXT,
            _PRIVATE_IDENTIFIER,
            _STREET_ADDRESS,
            _EMAIL,
            _URL,
            _PHONE,
        )
    )


def prepare_resume_text_for_groq(text: str) -> str | None:
    if _ACCESSIBILITY_TEXT.search(text) or _ACCOMMODATION_CONTEXT.search(text):
        return None
    if _PRIVATE_IDENTIFIER.search(text) or _STREET_ADDRESS.search(text):
        return None

    safe_lines: list[str] = []
    header_lines: list[str] = []
    in_professional_section = False
    found_professional_section = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        normalized_heading = re.sub(r"[^a-z0-9 ]+", " ", stripped.casefold())
        normalized_heading = re.sub(r"\s+", " ", normalized_heading).strip()
        heading = normalized_heading.rstrip(":").strip()
        if heading in _RESUME_SECTION_HEADINGS:
            in_professional_section = True
            found_professional_section = True
            continue
        if heading in _NONPROFESSIONAL_HEADINGS:
            in_professional_section = False
            continue

        is_heading = stripped.endswith(":") or (
            len(stripped.split()) <= 4 and stripped.isupper()
        )
        if is_heading:
            in_professional_section = False
            continue

        if not in_professional_section:
            if not found_professional_section:
                header_lines.append(stripped)
            continue

        safe_line = _EMAIL.sub("[REDACTED]", stripped)
        safe_line = _URL.sub("[REDACTED]", safe_line)
        safe_line = _PHONE.sub(
            lambda match: (
                "[REDACTED]"
                if sum(character.isdigit() for character in match.group()) >= 7
                else match.group()
            ),
            safe_line,
        )
        for header_value in header_lines:
            if (
                len(header_value.split()) <= 5
                and not re.search(r"\d|@|https?://|www\.", header_value, re.IGNORECASE)
            ):
                safe_line = re.sub(
                    re.escape(header_value),
                    "[REDACTED]",
                    safe_line,
                    flags=re.IGNORECASE,
                )
        safe_lines.append(safe_line)

    payload = "\n".join(safe_lines).strip()
    return payload if found_professional_section and payload else None


def sanitize_resume_profile_for_storage(profile: dict[str, Any]) -> dict[str, Any]:
    def scrub(value: Any) -> Any:
        if isinstance(value, str):
            if _ACCESSIBILITY_TEXT.search(value) or _ACCOMMODATION_CONTEXT.search(value):
                return None
            if _PRIVATE_IDENTIFIER.search(value) or _STREET_ADDRESS.search(value):
                return None
            value = _EMAIL.sub("[REDACTED]", value)
            value = _URL.sub("[REDACTED]", value)
            value = _PHONE.sub(
                lambda match: (
                    "[REDACTED]"
                    if sum(character.isdigit() for character in match.group()) >= 7
                    else match.group()
                ),
                value,
            )
            return value
        if isinstance(value, list):
            return [item for entry in value if (item := scrub(entry)) is not None]
        if isinstance(value, dict):
            cleaned = {}
            for key, entry in value.items():
                item = scrub(entry)
                if key == "name" and item is None and entry is not None:
                    return None
                cleaned[key] = item
            return cleaned
        return value

    sanitized = scrub(profile)
    if not isinstance(sanitized, dict):
        raise TypeError("Sanitized résumé profile must remain an object.")
    return sanitized


class GroqExtractionClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = GROQ_MODEL,
        client: Any = None,
    ) -> None:
        self._api_key = GROQ_API_KEY if api_key is None else api_key
        self._model_name = model
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            return None
        try:
            from groq import Groq
        except ImportError:
            raise GroqExtractionError(
                "Groq extraction requires the optional 'groq' package."
            ) from None
        try:
            self._client = Groq(api_key=self._api_key)
        except Exception:
            raise GroqExtractionError("Groq client initialization failed.") from None
        return self._client

    def _extract(
        self, text: str, schema: type[BaseModel], instruction: str
    ) -> BaseModel | None:
        if not self._api_key and self._client is None:
            return None
        if not text.strip():
            return None
        try:
            client = self._get_client()
            if client is None:
                return None
            schema_json = json.dumps(schema.model_json_schema())
            response = client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"{instruction}\nReturn JSON matching this schema:\n{schema_json}"
                            "\nMissing scalar values must be null; missing lists must be empty. "
                            "Do not infer or invent information."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty structured response.")
            return schema.model_validate_json(content)
        except Exception:
            raise GroqExtractionError("Groq structured extraction failed.") from None

    def extract_resume(self, resume_text: str) -> ResumeExtraction | None:
        safe_text = prepare_resume_text_for_groq(resume_text)
        if safe_text is None:
            raise PrivacyFilterError("Résumé payload did not pass privacy filtering.")
        result = self._extract(
            safe_text,
            ResumeExtraction,
            "Extract only information explicitly present in this résumé.",
        )
        return result if isinstance(result, ResumeExtraction) else None

    def enrich_job(
        self, job_text: str, requirements: list[dict[str, Any]]
    ) -> JobExtraction | None:
        del job_text
        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("requirement"), str)
            for item in requirements
        ):
            raise GroqExtractionError("Rule-based job requirements were invalid.")
        requirement_list = [str(item["requirement"]) for item in requirements]
        if any(not is_safe_professional_text(item) for item in requirement_list):
            raise PrivacyFilterError("Job requirement payload did not pass privacy filtering.")

        payload = (
            "Only these parser-derived professional requirements are permitted. "
            "Return one enrichment for each item in exactly the same order. Preserve each "
            "original_requirement string exactly. You may normalize wording, but must not "
            "add, remove, combine, or split requirements.\n"
            f"{json.dumps(requirement_list, ensure_ascii=False)}"
        )
        result = self._extract(
            payload,
            JobExtraction,
            "Extract job metadata and normalize only the supplied requirements.",
        )
        if result is None:
            return None
        returned = [item.original_requirement for item in result.requirement_enrichments]
        if returned != requirement_list:
            raise GroqExtractionError(
                "Groq changed the rule-based requirement list; enrichment was rejected."
            )
        return result

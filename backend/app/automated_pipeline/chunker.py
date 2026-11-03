from __future__ import annotations

import re
from typing import Any

CHUNK_SIZE_TOKENS = 180
CHUNK_OVERLAP_TOKENS = 30

_SECTION_HEADINGS = {
    "skills": "skills",
    "technical skills": "skills",
    "core competencies": "skills",
    "projects": "projects",
    "academic projects": "projects",
    "personal projects": "projects",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment": "experience",
    "education": "education",
    "academic background": "education",
    "certifications": "certifications",
    "summary": "summary",
    "professional summary": "summary",
    "about me": "summary",
    "requirements": "requirements",
    "job requirements": "requirements",
    "responsibilities": "responsibilities",
    "key responsibilities": "responsibilities",
    "qualifications": "qualifications",
}


def _detect_sections(text: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    current_section = "general"
    start_pos = 0
    cur_pos = 0

    for line in text.splitlines(keepends=True):
        clean_heading = re.sub(r"^#+\s*", "", line.strip()).rstrip(":").strip().casefold()
        if clean_heading in _SECTION_HEADINGS:
            if cur_pos > start_pos:
                spans.append((current_section, start_pos, cur_pos))
                current_section = _SECTION_HEADINGS[clean_heading]
                start_pos = cur_pos
            else:
                current_section = _SECTION_HEADINGS[clean_heading]
        cur_pos += len(line)

    if cur_pos > start_pos:
        spans.append((current_section, start_pos, cur_pos))
    if not spans and text:
        spans.append(("general", 0, len(text)))
    return spans


def chunk_text(
    text: str,
    *,
    chunk_size_tokens: int = CHUNK_SIZE_TOKENS,
    chunk_overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[dict[str, Any]]:
    """
    Chunks document text into overlapping passages with metadata and char offsets.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    sections = _detect_sections(clean_text)
    chunks: list[dict[str, Any]] = []

    for section_idx, (section_name, span_start, span_end) in enumerate(sections):
        section_text = clean_text[span_start:span_end]
        token_matches = list(re.finditer(r"\S+", section_text))
        if not token_matches:
            continue

        token_count = len(token_matches)
        start_token = 0

        while start_token < token_count:
            end_token = min(start_token + chunk_size_tokens, token_count)
            char_start = token_matches[start_token].start()
            char_end = token_matches[end_token - 1].end()

            passage_text = section_text[char_start:char_end].strip()
            if passage_text:
                idx = len(chunks)
                chunks.append(
                    {
                        "chunk_index": idx,
                        "chunk_text": passage_text,
                        "start_char": span_start + char_start,
                        "end_char": span_start + char_end,
                        "metadata": {
                            "section_name": section_name,
                            "section_index": section_idx,
                            "token_count": end_token - start_token,
                        },
                    }
                )

            if end_token == token_count:
                break
            step = chunk_size_tokens - chunk_overlap_tokens
            start_token += max(1, step)

    return chunks

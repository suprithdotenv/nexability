from __future__ import annotations

import re
from typing import Any

from .config import CHUNK_OVERLAP_TOKENS, CHUNK_SIZE_TOKENS
from .embeddings import create_tokenizer

_SECTION_HEADINGS = {
    "skills": "skills",
    "technical skills": "skills",
    "core concepts": "skills",
    "core competencies": "skills",
    "projects": "projects",
    "academic projects": "projects",
    "personal projects": "projects",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "experience & activities": "experience",
    "education": "education",
    "academic background": "education",
    "certifications": "certifications",
    "professional summary": "summary",
    "summary": "summary",
}


def _section_spans(text: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    section = "other"
    section_start = 0
    position = 0
    for line in text.splitlines(keepends=True):
        heading = re.sub(r"^#+\s*", "", line.strip()).rstrip(":").strip().casefold()
        next_section = _SECTION_HEADINGS.get(heading)
        if next_section is not None and position > section_start:
            spans.append((section, section_start, position))
            section = next_section
            section_start = position
        elif next_section is not None:
            section = next_section
        position += len(line)
    if position < len(text):
        position = len(text)
    if section_start < position:
        spans.append((section, section_start, position))
    if not spans and text:
        spans.append(("other", 0, len(text)))
    return spans


def _legacy_character_chunks(
    text: str, *, metadata: dict[str, Any], max_chars: int
) -> list[dict[str, Any]]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive.")
    chunks = []
    for index, start in enumerate(range(0, len(text), max_chars)):
        chunk_text = text[start : start + max_chars]
        chunks.append(
            {
                "chunk_index": index,
                "text": chunk_text,
                "metadata": {
                    **metadata,
                    "section_name": "document",
                    "section_index": 0,
                    "chunk_index": index,
                    "char_start": start,
                    "char_end": min(start + max_chars, len(text)),
                    "section_title": chunk_text.splitlines()[0][:80]
                    if chunk_text.splitlines()
                    else "",
                },
            }
        )
    return chunks


def chunk_document_text(
    text: str,
    *,
    metadata: dict[str, Any] | None = None,
    chunk_size_tokens: int = CHUNK_SIZE_TOKENS,
    chunk_overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    tokenizer: Any = None,
    max_chars: int | None = None,
) -> list[dict[str, Any]]:
    metadata = metadata or {}
    if not text:
        return []
    if max_chars is not None:
        return _legacy_character_chunks(text, metadata=metadata, max_chars=max_chars)
    if chunk_size_tokens < 1:
        raise ValueError("chunk_size_tokens must be positive.")
    if chunk_overlap_tokens < 0 or chunk_overlap_tokens >= chunk_size_tokens:
        raise ValueError("chunk_overlap_tokens must be non-negative and smaller than chunk size.")

    tokenizer = tokenizer or create_tokenizer()
    chunks: list[dict[str, Any]] = []
    for section_index, (section_name, span_start, span_end) in enumerate(_section_spans(text)):
        section_text = text[span_start:span_end]
        offsets = tokenizer.encode_with_offsets(section_text)
        if not offsets:
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "text": section_text,
                    "metadata": {
                        **metadata,
                        "section_name": section_name,
                        "section_index": section_index,
                        "chunk_index": len(chunks),
                        "char_start": span_start,
                        "char_end": span_end,
                    },
                }
            )
            continue

        start = 0
        while start < len(offsets):
            end = min(start + chunk_size_tokens, len(offsets))
            char_start = 0 if start == 0 else offsets[start][0]
            char_end = len(section_text) if end == len(offsets) else offsets[end][0]
            if char_end <= char_start:
                raise ValueError("Tokenizer returned invalid or non-progressing offsets.")
            index = len(chunks)
            chunks.append(
                {
                    "chunk_index": index,
                    "text": section_text[char_start:char_end],
                    "metadata": {
                        **metadata,
                        "section_name": section_name,
                        "section_index": section_index,
                        "chunk_index": index,
                        "char_start": span_start + char_start,
                        "char_end": span_start + char_end,
                    },
                }
            )
            if end == len(offsets):
                break
            next_start = end - chunk_overlap_tokens
            if next_start <= start:
                raise ValueError("Chunk overlap prevents tokenizer progress.")
            start = next_start
    return chunks


def chunk_sections(
    sections: list[str], *, metadata: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    metadata = metadata or {}
    chunks: list[dict[str, Any]] = []
    for index, section in enumerate(sections):
        clean = section.strip()
        if not clean:
            continue
        chunks.append(
            {
                "chunk_index": len(chunks),
                "text": clean,
                "metadata": {
                    **metadata,
                    "section_name": "other",
                    "section_index": index,
                    "chunk_index": len(chunks),
                    "char_start": None,
                    "char_end": None,
                },
            }
        )
    return chunks

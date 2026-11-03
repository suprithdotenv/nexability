from __future__ import annotations

import mimetypes
import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any
from xml.etree import ElementTree


@dataclass
class DocumentExtractionResult:
    filename: str
    mime_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    is_scanned: bool = False
    pages: int | None = None


def infer_mime_type(filename: str | None, content_type: str | None = None) -> str:
    if content_type:
        return content_type.split(";", 1)[0].strip().lower()
    guessed, _ = mimetypes.guess_type(filename or "")
    if guessed:
        return guessed.lower()
    raise ValueError("Could not infer a supported document type from filename or content type.")


def _extract_docx_text(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        if "word/document.xml" not in archive.namelist():
            return ""
        root = ElementTree.fromstring(archive.read("word/document.xml"))
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts: list[str] = []
        for paragraph in root.findall(".//w:p", namespace):
            text = "".join(
                node.text or "" for node in paragraph.findall(".//w:t", namespace)
            )
            if text:
                texts.append(text)
        return "\n".join(texts)


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(data))
        text_chunks: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text:
                text_chunks.append(page_text)
        return "\n\n".join(text_chunks)
    except Exception:
        pass

    try:
        import fitz  # type: ignore

        document = fitz.open(stream=data, filetype="pdf")
        text_chunks: list[str] = []
        for page in document:
            page_text = page.get_text("text")
            if page_text:
                text_chunks.append(page_text)
        return "\n\n".join(text_chunks)
    except Exception:
        pass

    return _pdf_text_fallback(data)


def _pdf_text_fallback(data: bytes) -> str:
    text = data.decode("latin-1", errors="ignore")
    matches = re.findall(r"BT\\s*(.*?)\\s*ET", text, flags=re.DOTALL)
    extracted: list[str] = []
    for block in matches:
        block = re.sub(r"\\\((.*?)\\\)", r"\1", block)
        block = re.sub(r"\\[0-9]+", "", block)
        block = block.replace("\\n", " ")
        cleaned = block.strip()
        if cleaned:
            extracted.append(cleaned)
    if extracted:
        return "\n".join(extracted)
    return ""


def parse_document_bytes(
    data: bytes, filename: str, content_type: str | None = None
) -> DocumentExtractionResult:
    mime_type = infer_mime_type(filename, content_type)
    lowered = mime_type.lower()
    if lowered == "application/pdf":
        parsed_text = _extract_pdf_text(data)
        is_scanned = not bool(parsed_text.strip())
        return DocumentExtractionResult(
            filename=filename,
            mime_type=mime_type,
            text=parsed_text,
            metadata={"source": "pdf", "extension": PurePosixPath(filename).suffix.lower()},
            is_scanned=is_scanned,
            pages=None,
        )

    if lowered in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/vnd.ms-word",
    }:
        parsed_text = _extract_docx_text(data)
        return DocumentExtractionResult(
            filename=filename,
            mime_type=mime_type,
            text=parsed_text,
            metadata={"source": "docx", "extension": PurePosixPath(filename).suffix.lower()},
            is_scanned=False,
            pages=None,
        )

    raise ValueError(f"Unsupported file type: {mime_type}. Supported types are PDF and DOCX.")

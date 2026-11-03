from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ML_DIRECTORY = Path(__file__).resolve().parents[1]
DOTENV_PATH = ML_DIRECTORY / ".env"
if not DOTENV_PATH.is_file():
    DOTENV_PATH = ML_DIRECTORY / "ml" / ".env"

load_dotenv(dotenv_path=DOTENV_PATH, override=False)


def _integer(name: str, default: int, *, minimum: int) -> int:
    raw_value = os.getenv(name)
    value = int(raw_value) if raw_value and raw_value.strip() else default
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return value


def _positive_int(name: str, default: int) -> int:
    return _integer(name, default, minimum=1)


def _configured_string(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _configured_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = _configured_string(name="GROQ_MODEL", default="openai/gpt-oss-120b")
NEXABILITY_LLM_EXTRACTION = _configured_bool("NEXABILITY_LLM_EXTRACTION", False)
E5_MODEL_NAME = "intfloat/e5-base-v2"
PLACEHOLDER_EMBEDDING_MODEL = "placeholder"
EMBEDDING_MODEL = _configured_string("EMBEDDING_MODEL", E5_MODEL_NAME)
EMBEDDING_DIM = _positive_int("EMBEDDING_DIM", 768)
CHUNK_SIZE_TOKENS = _positive_int("CHUNK_SIZE_TOKENS", 180)
CHUNK_OVERLAP_TOKENS = _integer("CHUNK_OVERLAP_TOKENS", 30, minimum=0)
if CHUNK_OVERLAP_TOKENS < 0 or CHUNK_OVERLAP_TOKENS >= CHUNK_SIZE_TOKENS:
    raise ValueError("CHUNK_OVERLAP_TOKENS must be non-negative and smaller than chunk size.")
RETRIEVAL_TOP_K = 3
PROFESSIONAL_MATCH_THRESHOLD: float = float(os.getenv('PROFESSIONAL_MATCH_THRESHOLD', '60.0'))

PROFESSIONAL_EVIDENCE_WEIGHTS = {
    "demonstrated": 1.0,
    "listed": 0.5,
    "partial": 0.25,
    "not_found": 0.0,
}

"""Public package interface for NexAbility ML components."""

from .accessibility_repository import AccessibilityProfileRepository
from .api_client import InternalMLClient
from .chunking import chunk_document_text, chunk_sections
from .embeddings import E5EmbeddingModel
from .groq_extraction import GroqExtractionClient
from .matcher import build_accessibility_summary, match_candidate_to_jobs
from .normalizer import normalize_job_description, normalize_resume_profile
from .ranking import compute_ranking_score, rank_and_select
from .parser import DocumentExtractionResult, parse_document_bytes
from .pipeline import NexAbilityMLPipeline
from .vectorstore import SimpleEmbeddingModel

__all__ = [
    "DocumentExtractionResult",
    "E5EmbeddingModel",
    "GroqExtractionClient",
    "InternalMLClient",
    "AccessibilityProfileRepository",
    "NexAbilityMLPipeline",
    "SimpleEmbeddingModel",
    "build_accessibility_summary",
    "chunk_document_text",
    "chunk_sections",
    "compute_ranking_score",
    "match_candidate_to_jobs",
    "normalize_job_description",
    "normalize_resume_profile",
    "parse_document_bytes",
    "rank_and_select",
]

__version__ = "0.1.0"

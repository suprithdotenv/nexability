from __future__ import annotations

import hashlib
import math
import re
from typing import Any

EMBEDDING_DIM = 768


class DeterministicEmbeddingEncoder:
    """
    Produces deterministic, normalized 768-dimensional dense vectors
    using token hashing. Fast, zero-overhead, works with pgvector in all environments.
    """
    def __init__(self, dimensions: int = EMBEDDING_DIM):
        self.dimensions = dimensions

    def encode(self, texts: list[str], *, prefix: str = "") -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            counts: dict[str, int] = {}
            tokens = re.findall(r"[A-Za-z0-9]+", (prefix + (text or "")).lower())
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            vector = [0.0] * self.dimensions
            for token, count in counts.items():
                bucket = (
                    int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
                    % self.dimensions
                )
                vector[bucket] += float(count)
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            results.append([round(v / norm, 6) for v in vector])
        return results

    def encode_single(self, text: str, *, prefix: str = "") -> list[float]:
        vectors = self.encode([text], prefix=prefix)
        return vectors[0] if vectors else [0.0] * self.dimensions


_e5_model_instance = None


def get_embedding_encoder():
    """
    Attempts to load SentenceTransformer E5 model; falls back to DeterministicEmbeddingEncoder
    if PyTorch/sentence-transformers are unavailable in the runtime environment.
    """
    global _e5_model_instance
    if _e5_model_instance is not None:
        return _e5_model_instance

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        class _SentenceTransformerWrapper:
            def __init__(self, model_name: str = "intfloat/e5-base-v2"):
                self.model = SentenceTransformer(model_name)
                self.dimensions = EMBEDDING_DIM

            def encode(self, texts: list[str], *, prefix: str = "passage: ") -> list[list[float]]:
                if not texts:
                    return []
                encoded = self.model.encode(
                    [prefix + t for t in texts],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )
                rows = encoded.tolist() if hasattr(encoded, "tolist") else encoded
                return [[float(x) for x in row] for row in rows]

            def encode_single(self, text: str, *, prefix: str = "passage: ") -> list[float]:
                return self.encode([text], prefix=prefix)[0]

        _e5_model_instance = _SentenceTransformerWrapper()
        return _e5_model_instance
    except Exception:
        _e5_model_instance = DeterministicEmbeddingEncoder(dimensions=EMBEDDING_DIM)
        return _e5_model_instance


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Computes cosine similarity between two 768-d unit vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a)) or 1.0
    norm_b = math.sqrt(sum(b * b for b in vec_b)) or 1.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))

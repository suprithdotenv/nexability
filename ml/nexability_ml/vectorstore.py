from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable

from .config import EMBEDDING_DIM


class SimpleEmbeddingModel:
    """Placeholder, not semantic; deterministic lexical vectors for tests/local use."""

    model_name = "placeholder, not semantic"

    def __init__(self, dimensions: int = EMBEDDING_DIM):
        self.dimensions = dimensions

    def encode(
        self, texts: Iterable[str], *, prefix: str = ""
    ) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            token_counts: dict[str, int] = {}
            for token in re.findall(r"[A-Za-z0-9]+", (prefix + (text or "")).lower()):
                token_counts[token] = token_counts.get(token, 0) + 1
            vector = [0.0 for _ in range(self.dimensions)]
            for token, count in token_counts.items():
                bucket = (
                    int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
                    % self.dimensions
                )
                vector[bucket] += float(count)
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            embeddings.append([value / norm for value in vector])
        return embeddings

    def encode_single(self, text: str) -> list[float]:
        vectors = self.encode([text])
        return vectors[0] if vectors else [0.0] * self.dimensions

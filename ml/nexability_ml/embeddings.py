from __future__ import annotations

import math
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

from .config import (
    E5_MODEL_NAME,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    PLACEHOLDER_EMBEDDING_MODEL,
    RETRIEVAL_TOP_K,
)
from .vectorstore import SimpleEmbeddingModel


class E5EmbeddingModel:
    """Lazy intfloat/e5-base-v2 encoder; never falls back to placeholder vectors."""

    def __init__(self, *, model_name: str = E5_MODEL_NAME, model_loader: Any = None):
        self.model_name = model_name
        self._model_loader = model_loader
        self._model: Any = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            if self._model_loader is not None:
                self._model = self._model_loader(self.model_name)
            else:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
        except Exception:
            raise RuntimeError(
                f"Could not load configured embedding model '{self.model_name}'. "
                "Install the optional E5 dependencies and retry."
            ) from None
        return self._model

    def encode(
        self,
        texts: Iterable[str],
        *,
        prefix: str = "passage: ",
    ) -> list[list[float]]:
        values = list(texts)
        if not values:
            return []
        model = self._load_model()
        try:
            encoded = model.encode(
                [prefix + text for text in values],
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            rows = encoded.tolist() if hasattr(encoded, "tolist") else encoded
            vectors = [[float(value) for value in row] for row in rows]
        except Exception:
            raise RuntimeError(
                f"Embedding failed for configured model '{self.model_name}'."
            ) from None

        if len(vectors) != len(values):
            raise RuntimeError("Embedding model returned an unexpected number of vectors.")
        for vector in vectors:
            if len(vector) != EMBEDDING_DIM:
                raise RuntimeError(
                    f"Embedding model returned {len(vector)} dimensions; "
                    f"configuration requires {EMBEDDING_DIM}."
                )
            norm = math.sqrt(sum(value * value for value in vector))
            if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
                raise RuntimeError("Embedding model returned a non-normalized vector.")
        return vectors


class WhitespaceTokenizer:
    """Small deterministic tokenizer for the explicit placeholder mode."""

    def encode_with_offsets(self, text: str) -> list[tuple[int, int]]:
        import re

        return [match.span() for match in re.finditer(r"\S+", text)]


@lru_cache(maxsize=2)
def _load_e5_tokenizer(model_name: str) -> Any:
    try:
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(model_name)
    except Exception:
        raise RuntimeError(
            f"Could not load tokenizer for configured embedding model '{model_name}'."
        ) from None


class E5Tokenizer:
    def __init__(self, *, model_name: str = E5_MODEL_NAME, tokenizer_loader: Any = None):
        self.model_name = model_name
        self._tokenizer_loader = tokenizer_loader
        self._tokenizer: Any = None

    def _load(self) -> Any:
        if self._tokenizer is None:
            self._tokenizer = (
                self._tokenizer_loader(self.model_name)
                if self._tokenizer_loader
                else _load_e5_tokenizer(self.model_name)
            )
        return self._tokenizer

    def encode_with_offsets(self, text: str) -> list[tuple[int, int]]:
        result = self._load()(
            text,
            add_special_tokens=False,
            truncation=False,
            return_offsets_mapping=True,
        )
        return [tuple(offset) for offset in result["offset_mapping"] if offset[1] > offset[0]]


def create_embedding_model(model_name: str = EMBEDDING_MODEL) -> Any:
    if model_name.casefold() in {
        PLACEHOLDER_EMBEDDING_MODEL,
        "simple",
        "simpleembeddingmodel",
    }:
        return SimpleEmbeddingModel(dimensions=EMBEDDING_DIM)
    if model_name == E5_MODEL_NAME:
        return E5EmbeddingModel(model_name=model_name)
    raise ValueError(
        f"Unsupported EMBEDDING_MODEL '{model_name}'. Use '{E5_MODEL_NAME}' "
        f"or '{PLACEHOLDER_EMBEDDING_MODEL}'."
    )


def create_tokenizer(model_name: str = EMBEDDING_MODEL) -> Any:
    if model_name.casefold() in {
        PLACEHOLDER_EMBEDDING_MODEL,
        "simple",
        "simpleembeddingmodel",
    }:
        return WhitespaceTokenizer()
    if model_name == E5_MODEL_NAME:
        return E5Tokenizer(model_name=model_name)
    raise ValueError(f"Unsupported tokenizer model '{model_name}'.")


def retrieve_resume_chunks(
    resume_text: str,
    requirements: list[str],
    *,
    embedding_model: Any,
    tokenizer: Any = None,
    top_k: int = RETRIEVAL_TOP_K,
) -> dict[str, list[str]]:
    if not resume_text.strip() or not requirements:
        return {}
    from .chunking import chunk_document_text

    chunks = chunk_document_text(resume_text, tokenizer=tokenizer)
    passage_vectors = embedding_model.encode(
        [chunk["text"] for chunk in chunks], prefix="passage: "
    )
    query_vectors = embedding_model.encode(requirements, prefix="query: ")
    if len(passage_vectors) != len(chunks) or len(query_vectors) != len(requirements):
        raise RuntimeError("Embedding model returned an unexpected number of retrieval vectors.")

    ranked: dict[str, list[str]] = {}
    for requirement, query in zip(requirements, query_vectors, strict=True):
        scores: list[tuple[float, int]] = []
        for index, passage in enumerate(passage_vectors):
            if len(passage) != len(query):
                raise RuntimeError("Query and passage embedding dimensions do not match.")
            scores.append((sum(a * b for a, b in zip(query, passage, strict=True)), index))
        scores.sort(key=lambda item: (-item[0], item[1]))
        ranked[requirement] = [
            chunks[index]["text"] for _, index in scores[: max(1, top_k)]
        ]
    return ranked

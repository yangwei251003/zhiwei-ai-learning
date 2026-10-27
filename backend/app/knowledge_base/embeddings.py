"""Embedding interfaces and the lazy production implementation."""

from math import isfinite
import threading
from typing import Protocol


DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class EmbeddingProtocol(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


def validate_embeddings(texts: list[str], vectors: list[list[float]]) -> list[list[float]]:
    if not texts:
        raise ValueError("embedding input must not be empty")
    if len(vectors) != len(texts):
        raise ValueError("embedding result count does not match input")
    dimension = len(vectors[0]) if vectors else 0
    if dimension == 0 or any(len(vector) != dimension for vector in vectors):
        raise ValueError("embedding vectors must have one non-zero dimension")
    normalized = [[float(value) for value in vector] for vector in vectors]
    if any(not isfinite(value) for vector in normalized for value in vector):
        raise ValueError("embedding vectors must contain finite numbers")
    return normalized


class LocalSentenceTransformerEmbedding:
    """Lazy local model; download/cache initialization errors are surfaced to callers."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL, model_factory=None) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be blank")
        self.model_name = model_name
        self._model = None
        self._model_factory = model_factory
        self._initialization_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise ValueError("embedding input must not be empty")
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("embedding texts must be non-blank strings")
        if self._model is None:
            with self._initialization_lock:
                if self._model is None:
                    factory = self._model_factory
                    if factory is None:
                        from sentence_transformers import SentenceTransformer

                        factory = SentenceTransformer
                    self._model = factory(self.model_name)
        with self._inference_lock:
            values = self._model.encode(texts, normalize_embeddings=True)
        vectors = values.tolist() if hasattr(values, "tolist") else values
        return validate_embeddings(texts, vectors)

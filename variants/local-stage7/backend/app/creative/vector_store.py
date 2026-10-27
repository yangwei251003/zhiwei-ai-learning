from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile
from threading import RLock
from typing import Any, Callable, Protocol

import faiss
import numpy as np


class Embedder(Protocol):
    dimension: int

    def encode(self, texts: list[str]) -> np.ndarray: ...


@dataclass(frozen=True)
class SearchResult:
    chunk_id: int
    score: float


class SentenceTransformerEmbedder:
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        *,
        dimension: int = 512,
        model_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.dimension = dimension
        self.model_name = model_name
        self._model_factory = model_factory or _load_sentence_transformer
        self._model: Any | None = None
        self._model_lock = RLock()

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    self._model = self._model_factory(self.model_name)
        return np.asarray(
            self._model.encode(
                texts, convert_to_numpy=True, normalize_embeddings=False
            ),
            dtype="float32",
        )


def _load_sentence_transformer(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class FaissVectorStore:
    def __init__(self, index_path: Path, embedder: Embedder) -> None:
        self.index_path = Path(index_path)
        self.embedder = embedder
        self._lock = RLock()
        if self.index_path.exists():
            self._index = _read_index_portably(self.index_path)
            if self._index.d != embedder.dimension:
                raise ValueError("已保存索引与 embedding 维度不匹配")
        else:
            self._index = faiss.IndexIDMap2(faiss.IndexFlatIP(embedder.dimension))

    @property
    def size(self) -> int:
        return self._index.ntotal

    def add(self, chunk_ids: list[int], texts: list[str]) -> None:
        if len(chunk_ids) != len(texts):
            raise ValueError("chunk ID 与文本数量必须一致")
        if not chunk_ids:
            return
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("chunk ID 不能重复")

        vectors = self._encode(texts)
        ids = np.asarray(chunk_ids, dtype="int64")
        with self._lock:
            existing = set(faiss.vector_to_array(self._index.id_map).tolist())
            if existing.intersection(chunk_ids):
                raise ValueError("chunk ID 已存在")
            self._index.add_with_ids(vectors, ids)
            self._persist()

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if limit <= 0:
            raise ValueError("limit 必须是正整数")
        with self._lock:
            if self._index.ntotal == 0:
                return []
            scores, ids = self._index.search(self._encode([query]), limit)
        return [
            SearchResult(int(chunk_id), float(score))
            for chunk_id, score in zip(ids[0], scores[0], strict=True)
            if chunk_id != -1
        ]

    def delete(self, chunk_ids: list[int]) -> int:
        if not chunk_ids:
            return 0
        with self._lock:
            removed = int(self._index.remove_ids(np.asarray(chunk_ids, dtype="int64")))
            if removed:
                self._persist()
        return removed

    def _encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.asarray(self.embedder.encode(texts), dtype="float32")
        expected = (len(texts), self.embedder.dimension)
        if vectors.shape != expected:
            raise ValueError(f"embedding 形状必须是 {expected}")
        faiss.normalize_L2(vectors)
        return vectors

    def _persist(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.index_path.with_suffix(self.index_path.suffix + ".tmp")
        descriptor, staging_name = tempfile.mkstemp(suffix=".faiss")
        os.close(descriptor)
        staging = Path(staging_name)
        try:
            faiss.write_index(self._index, str(staging))
            shutil.copyfile(staging, temporary)
            os.replace(temporary, self.index_path)
        finally:
            staging.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)


def _read_index_portably(index_path: Path):
    descriptor, staging_name = tempfile.mkstemp(suffix=".faiss")
    os.close(descriptor)
    staging = Path(staging_name)
    try:
        shutil.copyfile(index_path, staging)
        return faiss.read_index(str(staging))
    finally:
        staging.unlink(missing_ok=True)

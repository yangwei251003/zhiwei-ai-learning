import hashlib
import math
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.knowledge_base.chunking import TextChunk


class DeterministicEmbedding:
    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.lower().encode()).digest()
            vectors.append([float(digest[index]) / 255 for index in range(8)])
        return vectors


def test_store_rejects_empty_embedding_input_and_dimension_drift(tmp_path):
    from app.knowledge_base.embeddings import validate_embeddings

    with pytest.raises(ValueError, match="must not be empty"):
        validate_embeddings([], [])
    with pytest.raises(ValueError, match="dimension"):
        validate_embeddings(["a", "b"], [[1.0], [1.0, 2.0]])
    with pytest.raises(ValueError, match="dimension"):
        validate_embeddings(["a"], [[]])


def test_rag_store_filters_ranks_preserves_positions_and_reindexes(tmp_path):
    from app.knowledge_base.store import ChromaRAGStore

    store = ChromaRAGStore(tmp_path / "vectors", DeterministicEmbedding())
    chunks = [
        TextChunk("Neural NETWORK basics", "pdf", page=2, char_start=10, char_end=31),
        TextChunk("unrelated calculus", "pdf", page=3, char_start=32, char_end=50),
    ]
    store.index_document(1, 10, "AI", "lesson.pdf", chunks)
    store.index_document(2, 20, "AI", "private.pdf", [chunks[0]])
    store.index_document(1, 30, "Math", "math.pdf", [chunks[0]])

    results = store.search("network", user_id=1, course="AI", top_k=5)

    assert len(results) == 2
    hit = next(item for item in results if item["document_id"] == 10 and item["page"] == 2)
    assert hit["content"] == "Neural NETWORK basics"
    assert hit["char_start"] == 10 and hit["char_end"] == 31
    assert hit["paragraph"] is None
    assert 0 <= hit["similarity"] <= 1
    assert hit["citation_id"] == "10:0"
    assert hit["highlight_spans"] == [{"start": 7, "end": 14}]

    store.index_document(1, 10, "AI", "lesson.pdf", [chunks[0]])
    assert len(store.search("network", 1, "AI", 20)) == 1
    store.delete_document(1, 10)
    assert store.search("network", 1, "AI", 5) == []


def test_rag_store_validates_top_k_and_query(tmp_path):
    from app.knowledge_base.store import ChromaRAGStore

    store = ChromaRAGStore(tmp_path / "vectors", DeterministicEmbedding())
    for query, top_k in [("", 5), ("x", 0), ("x", 21)]:
        with pytest.raises(ValueError):
            store.search(query, 1, "AI", top_k)


def test_empty_tenant_course_search_does_not_load_embedding(tmp_path):
    from app.knowledge_base.store import ChromaRAGStore

    class MustNotLoadEmbedding:
        def encode(self, texts):
            raise AssertionError("empty collections must not initialize embeddings")

    store = ChromaRAGStore(tmp_path / "empty", MustNotLoadEmbedding())
    try:
        assert store.search("你好", user_id=1, course="AI", top_k=5) == []
    finally:
        store.close()


def test_rag_store_returns_top_five_in_descending_similarity_order(tmp_path):
    from app.knowledge_base.store import ChromaRAGStore

    scores = {
        "query": 1.0,
        "doc-1": 0.95,
        "doc-2": 0.80,
        "doc-3": 0.65,
        "doc-4": 0.50,
        "doc-5": 0.35,
        "doc-6": 0.20,
    }

    class SemanticEmbedding:
        def encode(self, texts):
            return [
                [scores[text], math.sqrt(1 - scores[text] ** 2)]
                for text in texts
            ]

    store = ChromaRAGStore(tmp_path / "semantic", SemanticEmbedding())
    for index in range(1, 7):
        store.index_document(
            1,
            100 + index,
            "AI",
            f"doc-{index}.txt",
            [TextChunk(f"doc-{index}", "txt", char_start=0, char_end=5)],
        )

    results = store.search("query", 1, "AI", top_k=5)

    assert [item["document_id"] for item in results] == [101, 102, 103, 104, 105]
    similarities = [item["similarity"] for item in results]
    assert similarities == sorted(similarities, reverse=True)


def test_local_embedding_constructs_once_and_serializes_inference():
    from app.knowledge_base.embeddings import LocalSentenceTransformerEmbedding

    constructed = 0
    active = 0
    max_active = 0
    guard = threading.Lock()

    class Values(list):
        def tolist(self):
            return list(self)

    class Model:
        def encode(self, texts, normalize_embeddings):
            nonlocal active, max_active
            with guard:
                active += 1
                max_active = max(max_active, active)
            threading.Event().wait(0.01)
            with guard:
                active -= 1
            return Values([[1.0, 0.0] for _ in texts])

    def factory(name):
        nonlocal constructed
        with guard:
            constructed += 1
        threading.Event().wait(0.01)
        return Model()

    embedding = LocalSentenceTransformerEmbedding("offline-model", model_factory=factory)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda index: embedding.encode([f"text-{index}"]), range(8)))

    assert constructed == 1
    assert max_active == 1
    assert results == [[[1.0, 0.0]]] * 8


def test_rag_store_close_is_idempotent_and_releases_windows_files(tmp_path):
    from app.knowledge_base.store import ChromaRAGStore

    path = tmp_path / "closable"
    store = ChromaRAGStore(path, DeterministicEmbedding())
    store.close()
    store.close()

    shutil.rmtree(path)
    assert not path.exists()

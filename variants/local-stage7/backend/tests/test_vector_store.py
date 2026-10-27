from __future__ import annotations

import numpy as np
import pytest

from app.creative.vector_store import FaissVectorStore, SentenceTransformerEmbedder


class FakeEmbedder:
    dimension = 3

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = {
            "Python 教程": [1.0, 0.0, 0.0],
            "Java 教程": [0.8, 0.2, 0.0],
            "历史知识": [0.0, 1.0, 0.0],
            "Python 问题": [1.0, 0.0, 0.0],
        }
        return np.asarray([vectors[text] for text in texts], dtype="float32")


def test_faiss_store_adds_and_searches_by_explicit_ids(tmp_path) -> None:
    store = FaissVectorStore(tmp_path / "index.faiss", FakeEmbedder())
    store.add([101, 205, 999], ["Python 教程", "Java 教程", "历史知识"])

    results = store.search("Python 问题", limit=2)

    assert [result.chunk_id for result in results] == [101, 205]
    assert results[0].score == pytest.approx(1.0)
    assert store.size == 3


def test_faiss_store_delete_keeps_other_ids_stable(tmp_path) -> None:
    store = FaissVectorStore(tmp_path / "index.faiss", FakeEmbedder())
    store.add([101, 205], ["Python 教程", "Java 教程"])

    assert store.delete([101]) == 1
    assert [result.chunk_id for result in store.search("Python 问题")] == [205]


def test_faiss_store_persists_and_reloads(tmp_path) -> None:
    index_path = tmp_path / "nested" / "index.faiss"
    store = FaissVectorStore(index_path, FakeEmbedder())
    store.add([101], ["Python 教程"])

    reloaded = FaissVectorStore(index_path, FakeEmbedder())

    assert reloaded.size == 1
    assert reloaded.search("Python 问题")[0].chunk_id == 101
    assert not index_path.with_suffix(".faiss.tmp").exists()


def test_faiss_store_persists_and_reloads_from_a_windows_unicode_path(tmp_path) -> None:
    index_path = tmp_path / "知识库索引" / "向量索引.faiss"
    store = FaissVectorStore(index_path, FakeEmbedder())

    store.add([101], ["Python 教程"])
    reloaded = FaissVectorStore(index_path, FakeEmbedder())

    assert index_path.exists()
    assert reloaded.search("Python 问题")[0].chunk_id == 101


def test_faiss_store_handles_empty_index_and_rejects_bad_input(tmp_path) -> None:
    store = FaissVectorStore(tmp_path / "index.faiss", FakeEmbedder())

    assert store.search("Python 问题") == []
    assert store.delete([404]) == 0
    with pytest.raises(ValueError, match="数量"):
        store.add([1, 2], ["Python 教程"])
    with pytest.raises(ValueError, match="正整数"):
        store.search("Python 问题", limit=0)


def test_sentence_transformer_embedder_loads_model_lazily() -> None:
    loaded: list[str] = []

    class Model:
        def encode(self, texts, **kwargs):
            assert kwargs["convert_to_numpy"] is True
            return np.ones((len(texts), 3), dtype="float32")

    def factory(name: str):
        loaded.append(name)
        return Model()

    embedder = SentenceTransformerEmbedder(
        "BAAI/test-model", dimension=3, model_factory=factory
    )
    assert loaded == []

    assert embedder.encode(["问题"]).shape == (1, 3)
    assert embedder.encode(["另一个问题"]).shape == (1, 3)
    assert loaded == ["BAAI/test-model"]

from __future__ import annotations

from sqlalchemy import select

from app.core.database import Base, build_engine, build_session_factory
from app.creative.vector_store import SearchResult
from app.models.database import KnowledgeChunk, KnowledgeDocument
from app.services.knowledge import KnowledgeService


class FakeVectorStore:
    def __init__(self) -> None:
        self.added: list[tuple[list[int], list[str]]] = []
        self.deleted: list[list[int]] = []
        self.results: list[SearchResult] = []

    def add(self, chunk_ids: list[int], texts: list[str]) -> None:
        self.added.append((chunk_ids, texts))

    def delete(self, chunk_ids: list[int]) -> int:
        self.deleted.append(chunk_ids)
        return len(chunk_ids)

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        return self.results[:limit]


def service(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'knowledge.db'}")
    Base.metadata.create_all(engine)
    vectors = FakeVectorStore()
    knowledge = KnowledgeService(
        build_session_factory(engine),
        vectors,
        tmp_path / "uploads",
        chunk_size=8,
        overlap=2,
        score_threshold=0.5,
    )
    return engine, vectors, knowledge


def test_ingest_document_saves_chunks_file_and_vectors(tmp_path) -> None:
    engine, vectors, knowledge = service(tmp_path)

    document = knowledge.ingest(
        "课程.txt", "text/plain", "Python基础知识很重要".encode()
    )

    assert document.status == "ready"
    assert document.chunk_count == 2
    assert (tmp_path / "uploads" / document.stored_path).read_bytes()
    with build_session_factory(engine)() as db:
        chunks = list(
            db.scalars(select(KnowledgeChunk).order_by(KnowledgeChunk.chunk_index))
        )
        assert [chunk.content for chunk in chunks] == ["Python基础", "基础知识很重要"]
        assert vectors.added == [
            ([chunk.id for chunk in chunks], [chunk.content for chunk in chunks])
        ]
    engine.dispose()


def test_retrieve_preserves_vector_rank_and_applies_evidence_threshold(
    tmp_path,
) -> None:
    engine, vectors, knowledge = service(tmp_path)
    knowledge.ingest("课程.txt", "text/plain", "Python基础知识很重要".encode())
    with build_session_factory(engine)() as db:
        chunks = list(
            db.scalars(select(KnowledgeChunk).order_by(KnowledgeChunk.chunk_index))
        )
    vectors.results = [
        SearchResult(chunks[1].id, 0.9),
        SearchResult(chunks[0].id, 0.6),
        SearchResult(999_999, 1.0),
    ]

    result = knowledge.retrieve("什么是 Python？")

    assert result.is_hit is True
    assert [hit.chunk_id for hit in result.hits] == [chunks[1].id, chunks[0].id]
    assert result.hits[0].source == "课程.txt"

    vectors.results = [SearchResult(chunks[0].id, 0.2)]
    weak = knowledge.retrieve("未知问题")
    assert weak.is_hit is False
    assert weak.hits == []
    engine.dispose()


def test_delete_document_removes_vectors_database_rows_and_file(tmp_path) -> None:
    engine, vectors, knowledge = service(tmp_path)
    document = knowledge.ingest("课程.txt", "text/plain", "Python基础".encode())
    stored_file = tmp_path / "uploads" / document.stored_path
    with build_session_factory(engine)() as db:
        chunk_ids = list(
            db.scalars(
                select(KnowledgeChunk.id).where(
                    KnowledgeChunk.document_id == document.id
                )
            )
        )

    assert knowledge.delete(document.id) is True
    assert vectors.deleted[-1] == chunk_ids
    assert not stored_file.exists()
    with build_session_factory(engine)() as db:
        assert db.get(KnowledgeDocument, document.id) is None
        assert db.scalars(select(KnowledgeChunk)).all() == []
    assert knowledge.delete(document.id) is False
    engine.dispose()


def test_ingest_parse_failure_leaves_no_database_or_file(tmp_path) -> None:
    engine, vectors, knowledge = service(tmp_path)

    try:
        knowledge.ingest("broken.txt", "text/plain", b"\xff")
    except ValueError as exc:
        assert "UTF-8" in str(exc)
    else:
        raise AssertionError("broken upload should fail")

    assert vectors.added == []
    assert list((tmp_path / "uploads").glob("*")) == []
    with build_session_factory(engine)() as db:
        assert db.scalars(select(KnowledgeDocument)).all() == []
    engine.dispose()


def test_vector_failure_rolls_back_without_deleting_unadded_ids(tmp_path) -> None:
    engine, vectors, knowledge = service(tmp_path)

    def fail_add(chunk_ids: list[int], texts: list[str]) -> None:
        raise RuntimeError("embedding failed")

    vectors.add = fail_add
    try:
        knowledge.ingest("课程.txt", "text/plain", "Python基础".encode())
    except RuntimeError as exc:
        assert str(exc) == "embedding failed"
    else:
        raise AssertionError("vector failure should propagate")

    assert vectors.deleted == []
    assert list((tmp_path / "uploads").glob("*")) == []
    with build_session_factory(engine)() as db:
        assert db.scalars(select(KnowledgeDocument)).all() == []
    engine.dispose()

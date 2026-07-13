"""SQL-backed knowledge retrieval for Supabase PostgreSQL and pgvector."""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from app.knowledge_base.chunking import TextChunk
from app.knowledge_base.embeddings import EmbeddingProtocol, validate_embeddings
from app.knowledge_base.store import _highlight_spans
from app.models import KnowledgeChunk


class SupabaseRAGStore:
    def __init__(self, session_factory: sessionmaker, embedding: EmbeddingProtocol) -> None:
        self.session_factory = session_factory
        self.embedding = embedding

    def close(self) -> None:
        return None

    def _uses_pgvector(self) -> bool:
        bind = self.session_factory.kw.get("bind")
        return bind is not None and bind.dialect.name == "postgresql"

    def index_document(self, user_id: int, document_id: int, course: str, filename: str, chunks: list[TextChunk]) -> int:
        if not chunks:
            raise ValueError("chunks must not be empty")
        vectors = [None] * len(chunks)
        if self._uses_pgvector():
            try:
                vectors = validate_embeddings(
                    [chunk.text for chunk in chunks], self.embedding.encode([chunk.text for chunk in chunks])
                )
            except Exception:
                pass
        session = self.session_factory()
        try:
            session.query(KnowledgeChunk).filter(
                KnowledgeChunk.user_id == user_id,
                KnowledgeChunk.document_id == document_id,
            ).delete(synchronize_session=False)
            session.add_all([
                KnowledgeChunk(
                    user_id=user_id, document_id=document_id, course=course, filename=filename,
                    source_type=chunk.source_type, chunk_index=index, content=chunk.text,
                    page=chunk.page, paragraph=chunk.paragraph, char_start=chunk.char_start,
                    char_end=chunk.char_end, embedding=vector,
                )
                for index, (chunk, vector) in enumerate(zip(chunks, vectors))
            ])
            session.commit()
            return len(chunks)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_document(self, user_id: int, document_id: int) -> None:
        session = self.session_factory()
        try:
            session.query(KnowledgeChunk).filter(
                KnowledgeChunk.user_id == user_id,
                KnowledgeChunk.document_id == document_id,
            ).delete(synchronize_session=False)
            session.commit()
        finally:
            session.close()

    def count_document(self, user_id: int, document_id: int) -> int:
        session = self.session_factory()
        try:
            return session.query(KnowledgeChunk).filter(
                KnowledgeChunk.user_id == user_id,
                KnowledgeChunk.document_id == document_id,
            ).count()
        finally:
            session.close()

    def search(self, query: str, user_id: int, course: str, top_k: int = 5) -> list[dict]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must not be blank")
        if type(top_k) is not int or not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        terms = [term.casefold() for term in query.split() if term.strip()]
        session = self.session_factory()
        try:
            if self._uses_pgvector():
                try:
                    query_vector = validate_embeddings([query], self.embedding.encode([query]))[0]
                    distance = KnowledgeChunk.embedding.cosine_distance(query_vector)
                    rows = session.query(KnowledgeChunk, distance.label("distance")).filter(
                        KnowledgeChunk.user_id == user_id,
                        KnowledgeChunk.course == course,
                        KnowledgeChunk.embedding.is_not(None),
                    ).order_by(distance, KnowledgeChunk.chunk_index).limit(top_k).all()
                    if rows:
                        return [self._serialize_hit(row, max(0.0, 1.0 - float(distance)), query) for row, distance in rows]
                except Exception:
                    session.rollback()
            rows = session.query(KnowledgeChunk).filter(
                KnowledgeChunk.user_id == user_id,
                KnowledgeChunk.course == course,
            ).all()
        finally:
            session.close()
        ranked = []
        for row in rows:
            matched = sum(term in row.content.casefold() for term in terms)
            if matched:
                ranked.append((matched / max(1, len(terms)), row))
        ranked.sort(key=lambda item: (-item[0], item[1].chunk_index))
        return [self._serialize_hit(row, score, query) for score, row in ranked[:top_k]]

    @staticmethod
    def _serialize_hit(row: KnowledgeChunk, similarity: float, query: str) -> dict:
        return {
            "content": row.content, "document_id": row.document_id, "filename": row.filename,
            "source_type": row.source_type, "page": row.page, "paragraph": row.paragraph,
            "char_start": row.char_start, "char_end": row.char_end, "similarity": similarity,
            "citation_id": f"{row.document_id}:{row.chunk_index}",
            "highlight_spans": _highlight_spans(row.content, query),
        }

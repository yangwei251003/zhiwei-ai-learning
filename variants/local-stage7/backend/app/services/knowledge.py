from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm import selectinload

from app.creative.vector_store import SearchResult
from app.models.database import KnowledgeChunk, KnowledgeDocument
from app.services.documents import (
    DocumentParseError,
    chunk_sections,
    parse_document,
    validate_document_upload,
)


class VectorStore(Protocol):
    def add(self, chunk_ids: list[int], texts: list[str]) -> None: ...

    def delete(self, chunk_ids: list[int]) -> int: ...

    def search(self, query: str, limit: int = 5) -> list[SearchResult]: ...


@dataclass(frozen=True)
class KnowledgeHit:
    chunk_id: int
    document_id: int
    content: str
    source: str
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    is_hit: bool
    hits: list[KnowledgeHit]


class KnowledgeService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        vector_store: VectorStore,
        upload_dir: Path,
        *,
        chunk_size: int = 800,
        overlap: int = 120,
        score_threshold: float = 0.35,
    ) -> None:
        if not 0 <= score_threshold <= 1:
            raise ValueError("score_threshold 必须在 0 到 1 之间")
        self.session_factory = session_factory
        self.vector_store = vector_store
        self.upload_dir = Path(upload_dir)
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.score_threshold = score_threshold

    def ingest(
        self, filename: str, content_type: str, payload: bytes
    ) -> KnowledgeDocument:
        safe_filename = Path(filename).name
        validate_document_upload(safe_filename, content_type, payload)
        sections = parse_document(safe_filename, payload)
        chunks = chunk_sections(
            sections, chunk_size=self.chunk_size, overlap=self.overlap
        )
        if not chunks:
            raise DocumentParseError("文档没有可索引文本")

        stored_name = f"{uuid4().hex}{Path(safe_filename).suffix.lower()}"
        stored_file = self.upload_dir / stored_name
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        stored_file.write_bytes(payload)

        indexed_ids: list[int] = []
        vectors_added = False
        with self.session_factory() as db:
            try:
                document = KnowledgeDocument(
                    filename=safe_filename,
                    stored_path=stored_name,
                    content_type=content_type or "application/octet-stream",
                    size_bytes=len(payload),
                    status="processing",
                )
                db.add(document)
                db.flush()
                records = [
                    KnowledgeChunk(
                        document_id=document.id,
                        chunk_index=position,
                        content=chunk.text,
                        metadata_json=json.dumps(
                            chunk.metadata, ensure_ascii=False, sort_keys=True
                        ),
                    )
                    for position, chunk in enumerate(chunks)
                ]
                db.add_all(records)
                db.flush()
                indexed_ids = [record.id for record in records]
                self.vector_store.add(
                    indexed_ids, [record.content for record in records]
                )
                vectors_added = True
                document.status = "ready"
                document.chunk_count = len(records)
                db.commit()
                db.refresh(document)
                return document
            except Exception:
                db.rollback()
                if vectors_added:
                    self.vector_store.delete(indexed_ids)
                stored_file.unlink(missing_ok=True)
                raise

    def retrieve(self, query: str, limit: int = 5) -> RetrievalResult:
        ranked = [
            result
            for result in self.vector_store.search(query, limit)
            if result.score >= self.score_threshold
        ]
        if not ranked:
            return RetrievalResult(is_hit=False, hits=[])

        ids = [result.chunk_id for result in ranked]
        with self.session_factory() as db:
            chunks = db.scalars(
                select(KnowledgeChunk)
                .options(selectinload(KnowledgeChunk.document))
                .where(KnowledgeChunk.id.in_(ids))
            ).all()
            by_id = {chunk.id: chunk for chunk in chunks}
            hits = [
                KnowledgeHit(
                    chunk_id=result.chunk_id,
                    document_id=by_id[result.chunk_id].document_id,
                    content=by_id[result.chunk_id].content,
                    source=by_id[result.chunk_id].document.filename,
                    score=result.score,
                )
                for result in ranked
                if result.chunk_id in by_id
            ]
        return RetrievalResult(is_hit=bool(hits), hits=hits)

    def delete(self, document_id: int) -> bool:
        with self.session_factory() as db:
            document = db.scalar(
                select(KnowledgeDocument)
                .options(selectinload(KnowledgeDocument.chunks))
                .where(KnowledgeDocument.id == document_id)
            )
            if document is None:
                return False
            chunk_ids = [chunk.id for chunk in document.chunks]
            contents = [chunk.content for chunk in document.chunks]
            stored_file = self.upload_dir / document.stored_path
            self.vector_store.delete(chunk_ids)
            try:
                db.delete(document)
                db.commit()
            except Exception:
                db.rollback()
                self.vector_store.add(chunk_ids, contents)
                raise
        stored_file.unlink(missing_ok=True)
        return True

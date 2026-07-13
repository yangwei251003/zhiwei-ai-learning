from functools import lru_cache

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.core import get_settings
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.knowledge_base.embeddings import LocalSentenceTransformerEmbedding
from app.knowledge_base.loaders import MAX_FILE_BYTES
from app.knowledge_base.supabase_store import SupabaseRAGStore
from app.knowledge_base.supabase_storage import SupabaseStorage
from app.models import User
from app.schemas import KnowledgeDocumentOut, KnowledgeSearchHit, KnowledgeSearchRequest
from app.services.knowledge_service import (
    KnowledgeNotFoundError, KnowledgeService, KnowledgeTooLargeError,
    KnowledgeUnavailableError, KnowledgeValidationError, LLMDocumentSummarizer,
)

router = APIRouter()


@lru_cache
def get_knowledge_service() -> KnowledgeService:
    settings = get_settings()
    embedding = LocalSentenceTransformerEmbedding(settings.embedding_model)
    if settings.uses_supabase_rag:
        storage = SupabaseStorage(
            settings.supabase_url,
            settings.supabase_service_role_key,
            settings.supabase_storage_bucket,
        )
        return KnowledgeService(
            SupabaseRAGStore(SessionLocal, embedding),
            settings.knowledge_upload_dir,
            LLMDocumentSummarizer(),
            object_storage=storage,
        )
    from app.knowledge_base.store import ChromaRAGStore
    return KnowledgeService(
        ChromaRAGStore(settings.vector_db_path, embedding),
        settings.knowledge_upload_dir,
        LLMDocumentSummarizer(),
    )


def _raise_service_error(exc: Exception):
    if isinstance(exc, KnowledgeNotFoundError):
        raise HTTPException(404, "document not found")
    if isinstance(exc, KnowledgeTooLargeError):
        raise HTTPException(413, str(exc))
    if isinstance(exc, KnowledgeValidationError):
        raise HTTPException(400, str(exc))
    if isinstance(exc, KnowledgeUnavailableError):
        raise HTTPException(503, str(exc))
    raise exc


@router.post("/upload", response_model=KnowledgeDocumentOut, status_code=201)
def upload_knowledge(
    file: UploadFile = File(...), course: str = Form(...),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    data = file.file.read(MAX_FILE_BYTES + 1)
    try:
        document = service.upload(
            db, user.id, file.filename or "", file.content_type or "", course, data
        )
        return service.serialize(document)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/list", response_model=list[KnowledgeDocumentOut])
def list_knowledge(
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    documents = service.list(db, user.id)
    return [service.serialize(item) for item in documents]


@router.post("/search", response_model=list[KnowledgeSearchHit])
def search_knowledge(
    request: KnowledgeSearchRequest, user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.search(request.query, user.id, request.course, request.top_k)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(503, "knowledge search is unavailable") from exc


@router.get("/{document_id}", response_model=KnowledgeDocumentOut)
def get_document(
    document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        document = service.get(db, user.id, document_id)
        return service.serialize(document)
    except Exception as exc:
        _raise_service_error(exc)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        service.delete(db, user.id, document_id)
        return Response(status_code=204)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{document_id}/reindex", response_model=KnowledgeDocumentOut)
def reindex_document(
    document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        document = service.reindex(db, user.id, document_id)
        return service.serialize(document)
    except Exception as exc:
        _raise_service_error(exc)

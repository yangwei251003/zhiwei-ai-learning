from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import envelope
from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.database import KnowledgeDocument, User
from app.schemas.knowledge import KnowledgeDocumentResponse
from app.services.documents import DocumentParseError
from app.services.knowledge import KnowledgeService


router = APIRouter(prefix="/knowledge", tags=["知识库"])


def get_knowledge_service(request: Request) -> KnowledgeService:
    settings = request.app.state.settings
    return KnowledgeService(
        request.app.state.session_factory,
        request.app.state.vector_store,
        settings.knowledge_upload_dir,
        score_threshold=settings.retrieval_score_threshold,
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    _: Annotated[User, Depends(require_admin)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    payload = await file.read(request.app.state.settings.max_upload_bytes + 1)
    if len(payload) > request.app.state.settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="文件超过上传大小限制")
    try:
        document = service.ingest(
            file.filename, file.content_type or "application/octet-stream", payload
        )
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope(KnowledgeDocumentResponse.model_validate(document), "上传成功", 201)


@router.get("/")
def list_documents(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    documents = db.scalars(
        select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    ).all()
    return envelope(
        [
            KnowledgeDocumentResponse.model_validate(document).model_dump(mode="json")
            for document in documents
        ]
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    _: Annotated[User, Depends(require_admin)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> dict:
    if not service.delete(document_id):
        raise HTTPException(status_code=404, detail="知识文档不存在")
    return envelope({"id": document_id}, "删除成功")

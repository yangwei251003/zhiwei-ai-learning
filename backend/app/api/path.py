from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.llm.service import LLMService
from app.models import User
from app.schemas.path import PathGenerateRequest, PathOut, PathProgressRequest
from app.services.path_service import PathNotFound, PathService, PathValidationError
from app.services.profile_service import ProfileService

router = APIRouter()


def get_path_service(db: Session = Depends(get_db)) -> PathService:
    # Import lazily so importing the router never initializes the embedding model.
    from app.api.knowledge import get_knowledge_service
    return PathService(db, LLMService(), get_knowledge_service(), ProfileService(db))


def _not_found(exc):
    raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/generate", response_model=PathOut, status_code=status.HTTP_201_CREATED)
async def generate_path(request: PathGenerateRequest, user: User = Depends(get_current_user), service: PathService = Depends(get_path_service)):
    try:
        return await service.generate(user.id, request.message, request.course)
    except PathValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/current", response_model=PathOut)
def current_path(user: User = Depends(get_current_user), service: PathService = Depends(get_path_service)):
    try: return service.current(user.id)
    except PathNotFound as exc: _not_found(exc)


@router.patch("/{path_id}/progress", response_model=PathOut)
def update_progress(path_id: int, request: PathProgressRequest, user: User = Depends(get_current_user), service: PathService = Depends(get_path_service)):
    try: return service.update_progress(user.id, path_id, request.step, request.status)
    except PathNotFound as exc: _not_found(exc)
    except PathValidationError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc

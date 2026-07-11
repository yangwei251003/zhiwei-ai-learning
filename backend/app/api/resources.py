from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import LearningResource, User
from app.schemas.resources import GenerateRequest, ResourceCreate, ResourcePage, ResourcePatch, ResourceResponse
from app.services.resource_service import ResourceGenerationError, ResourceGenerationService

router = APIRouter()


def get_resource_generation_service(db: Session = Depends(get_db)):
    from app.api.knowledge import get_knowledge_service
    from app.llm.service import LLMService
    from app.services.achievement_service import AchievementService
    return ResourceGenerationService(LLMService(), get_knowledge_service(), db, AchievementService(db))


def _owned(db, user_id, resource_id):
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id, LearningResource.user_id == user_id).first()
    if not resource: raise HTTPException(status_code=404, detail="资源不存在")
    return resource


@router.get("/", response_model=ResourcePage)
def list_resources(resource_type: str = None, skip: int = 0, limit: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(LearningResource).filter(LearningResource.user_id == user.id)
    if resource_type: query = query.filter(LearningResource.resource_type == resource_type)
    return ResourcePage(resources=[ResourceResponse.model_validate(r) for r in query.order_by(LearningResource.created_at.desc()).offset(skip).limit(limit).all()], total=query.count())


@router.post("/", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource(data: ResourceCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resource = LearningResource(user_id=user.id, resource_type=data.resource_type, title=data.title, content=data.content, rendered_html=data.rendered_html, metadata_json=data.metadata)
    db.add(resource); db.commit(); db.refresh(resource)
    return ResourceResponse.model_validate(resource)


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_resources(data: GenerateRequest, user: User = Depends(get_current_user), service: ResourceGenerationService = Depends(get_resource_generation_service)):
    try:
        return await service.generate_all(user, data.topic, data.course, data.profile)
    except ResourceGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ResourceResponse.model_validate(_owned(db, user.id, resource_id))


@router.patch("/{resource_id}", response_model=ResourceResponse)
def patch_resource(resource_id: int, data: ResourcePatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resource = _owned(db, user.id, resource_id)
    changes = data.model_dump(exclude_unset=True)
    if "title" in changes: resource.title = changes["title"]
    if "metadata" in changes: resource.metadata_json = changes["metadata"]
    db.commit(); db.refresh(resource)
    return ResourceResponse.model_validate(resource)


@router.delete("/{resource_id}")
def delete_resource(resource_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resource = _owned(db, user.id, resource_id); db.delete(resource); db.commit()
    return {"message": "删除成功"}

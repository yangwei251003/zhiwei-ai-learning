from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.auth import envelope
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.database import Resource, User
from app.schemas.resources import ResourceResponse


router = APIRouter(prefix="/resources", tags=["学习资源"])


@router.get("/")
def list_resources(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    resource_type: Annotated[str | None, Query(alias="type")] = None,
    search: str | None = None,
    sort: Literal["latest", "oldest"] = "latest",
) -> dict:
    statement = select(Resource).where(Resource.user_id == current_user.id)
    if resource_type:
        statement = statement.where(Resource.resource_type == resource_type)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(Resource.title.ilike(pattern), Resource.content.ilike(pattern))
        )
    ordering = (
        Resource.created_at.desc() if sort == "latest" else Resource.created_at.asc()
    )
    records = db.scalars(statement.order_by(ordering, Resource.id)).all()
    return envelope(
        [
            ResourceResponse.model_validate(record).model_dump(mode="json")
            for record in records
        ]
    )


@router.get("/{resource_id}")
def get_resource(
    resource_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    resource = db.scalar(
        select(Resource).where(
            Resource.id == resource_id, Resource.user_id == current_user.id
        )
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="学习资源不存在")
    return envelope(ResourceResponse.model_validate(resource))

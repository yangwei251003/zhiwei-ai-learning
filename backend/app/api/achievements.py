from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.services.achievement_service import AchievementService
router = APIRouter()
@router.get("")
def achievements(user: User=Depends(get_current_user), db=Depends(get_db)): return AchievementService(db).list_for_user(user.id)
@router.get("/progress")
def progress(user: User=Depends(get_current_user), db=Depends(get_db)):
    rows = AchievementService(db).list_for_user(user.id)
    return {"unlocked": sum(x["unlocked"] for x in rows), "total": len(rows), "achievements": rows}

from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas.creative import ChallengeAnswerIn
from app.services.challenge_service import ChallengeNotFound, ChallengeService, InvalidChallenge

router = APIRouter()
def get_challenge_llm():
    from app.llm.service import LLMService
    return LLMService()
def get_challenge_rag():
    from app.api.knowledge import get_knowledge_service
    return get_knowledge_service()
def get_challenge_profile(db=Depends(get_db)):
    from app.services.profile_service import ProfileService
    return ProfileService(db)
def get_challenge_achievements(db=Depends(get_db)):
    from app.services.achievement_service import AchievementService
    return AchievementService(db)
def get_challenge_service(db=Depends(get_db), llm=Depends(get_challenge_llm), rag=Depends(get_challenge_rag), profile=Depends(get_challenge_profile), achievements=Depends(get_challenge_achievements)):
    return ChallengeService(db, llm=llm, rag=rag, profile=profile, achievement=achievements)
def public(item):
    return {"id": item.id, "course": item.course, "date": item.challenge_date, "question_type": item.question_type, "question": item.question, "options": item.options, "difficulty": item.difficulty, "concept": item.concept, "reward_points": item.reward_points, "status": item.status}
@router.get("/today")
def today(course: str, user: User=Depends(get_current_user), svc=Depends(get_challenge_service)):
    item=svc.today_for(user.id, course)
    if not item: raise HTTPException(404, "今日挑战不存在")
    return public(item)
@router.post("/generate")
def generate(course: str, user: User=Depends(get_current_user), svc=Depends(get_challenge_service)):
    try: return public(svc.generate(user.id, course))
    except InvalidChallenge: raise HTTPException(422, "题目结构无效")
@router.post("/{challenge_id}/submit")
def submit(challenge_id: int, body: ChallengeAnswerIn, user: User=Depends(get_current_user), svc=Depends(get_challenge_service)):
    try: return svc.submit(user.id, challenge_id, body.answer)
    except ChallengeNotFound: raise HTTPException(404, "挑战不存在")
@router.get("/history")
def history(course: str|None=None, user: User=Depends(get_current_user), svc=Depends(get_challenge_service)): return [public(x) for x in svc.history(user.id, course)]

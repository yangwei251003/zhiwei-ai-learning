from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.models import AchievementDefinition, PointTransaction, UserAchievement

SEEDS = (
    ("first_chat", "初次交流", "完成首次对话", "chat_completed", 1, 10),
    ("five_resources", "资源收集者", "生成五类资源", "resources_generated", 5, 20),
    ("first_challenge", "迎接挑战", "完成首次挑战", "challenge_completed", 1, 10),
    ("three_day_streak", "坚持三日", "连续学习三天", "learning_streak", 3, 30),
    ("ten_graph_nodes", "知识织网", "掌握十个知识点", "graph_mastery_updated", 10, 25),
)
RESOURCE_TYPES = {"document", "mindmap", "quiz", "video_script", "code_case"}
EVALUATORS = {
    "first_chat": lambda event, metrics: (1 if event == "chat_completed" else 0),
    "five_resources": lambda event, metrics: (len(RESOURCE_TYPES & set(metrics.get("resource_types", ()))) if event == "resources_generated" else 0),
    "first_challenge": lambda event, metrics: (1 if event == "challenge_completed" else 0),
    "three_day_streak": lambda event, metrics: (float(metrics.get("consecutive_days", 0)) if event == "learning_streak" else 0),
    "ten_graph_nodes": lambda event, metrics: (float(metrics.get("mastered_nodes", 0)) if event == "graph_mastery_updated" else 0),
}


class AchievementService:
    def __init__(self, db): self.db = db; self.seed()
    def seed(self):
        existing = {x.code: x for x in self.db.query(AchievementDefinition).all()}
        for code, title, desc, rule, threshold, points in SEEDS:
            if code not in existing:
                self.db.add(AchievementDefinition(code=code, title=title, description=desc, badge=code, rule_type=rule, threshold=threshold, points=points))
            else:
                existing[code].rule_type = rule
        self.db.commit()

    def evaluate(self, user_id, event, metrics, commit=True):
        unlocked = []
        for definition in self.db.query(AchievementDefinition).filter_by(rule_type=event).all():
            evaluator = EVALUATORS.get(definition.code)
            value = float(evaluator(event, metrics) if evaluator else 0)
            ua = self.db.query(UserAchievement).filter_by(user_id=user_id, achievement_id=definition.id).first()
            if ua is None: ua = UserAchievement(user_id=user_id, achievement_id=definition.id); self.db.add(ua)
            ua.progress = max(float(ua.progress or 0), min(1.0, value / definition.threshold))
            if value >= definition.threshold and ua.unlocked_at is None:
                ua.unlocked_at = datetime.now(timezone.utc); unlocked.append(definition.code)
                self.db.add(PointTransaction(user_id=user_id, delta=definition.points, reason=definition.title, reference_type="achievement", reference_id=definition.id, idempotency_key=f"achievement:{user_id}:{definition.code}"))
        if commit:
            try: self.db.commit()
            except IntegrityError: self.db.rollback()
        else:
            self.db.flush()
        return unlocked

    def record_chat_completed(self, user_id):
        return self.evaluate(user_id, "chat_completed", {})

    def list_for_user(self, user_id):
        rows = {x.achievement_id: x for x in self.db.query(UserAchievement).filter_by(user_id=user_id)}
        return [{"code": d.code, "title": d.title, "description": d.description, "badge": d.badge, "points": d.points, "progress": rows[d.id].progress if d.id in rows else 0, "unlocked": bool(d.id in rows and rows[d.id].unlocked_at), "unlocked_at": rows[d.id].unlocked_at if d.id in rows else None} for d in self.db.query(AchievementDefinition).all()]

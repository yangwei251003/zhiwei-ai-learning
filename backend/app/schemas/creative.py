from typing import Literal
from pydantic import BaseModel, Field

class GraphNodeIn(BaseModel):
    key: str = Field(min_length=1, max_length=150); label: str = Field(min_length=1, max_length=200)
    difficulty: float = Field(0, ge=0, le=1); mastery: float = Field(0, ge=0, le=1)
    status: str = "locked"; resource_ids: list[int] = []; metadata_json: dict = {}
class GraphEdgeIn(BaseModel):
    source: int; target: int; relation: Literal["prerequisite", "related", "applied_by"]
    weight: float = Field(1, ge=0); metadata_json: dict = {}
class GraphRebuildIn(BaseModel): nodes: list[GraphNodeIn]; edges: list[dict] = []
class ChallengeAnswerIn(BaseModel): answer: str = Field(min_length=1)


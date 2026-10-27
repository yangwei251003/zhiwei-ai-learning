from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

ResourceType = Literal["document", "quiz", "mindmap", "video_script", "code_case"]
StepStatus = Literal["pending", "in_progress", "completed"]
NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PathStep(BaseModel):
    step: int = Field(ge=1)
    topic: NonBlank
    description: NonBlank
    estimated_minutes: int = Field(gt=0)
    resource_types_needed: list[ResourceType]
    status: StepStatus = "pending"


class PathPlan(BaseModel):
    steps: list[PathStep] = Field(min_length=5, max_length=8)


class PathGenerateRequest(BaseModel):
    message: Annotated[NonBlank, StringConstraints(max_length=2000)]
    course: Annotated[NonBlank, StringConstraints(max_length=200)]


class PathProgressRequest(BaseModel):
    step: int = Field(ge=1)
    status: StepStatus


class PathOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    path_data: list[PathStep]
    current_step: int
    is_active: bool

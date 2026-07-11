from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SummaryCard(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    highlights: Annotated[list[str], Field(min_length=3, max_length=3)]
    duration: str = Field(min_length=1)
    difficulty: int = Field(ge=1, le=5)


class ResourceBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary_card: SummaryCard
    tips: Annotated[list[str], Field(min_length=3, max_length=3)]
    citations: list[str]


class DocumentResult(ResourceBase):
    markdown: str

    @field_validator("markdown")
    @classmethod
    def valid_document(cls, value):
        if not value.lstrip().startswith("# ") or "\n## " not in value or "```" not in value or ("summary" not in value.lower() and "总结" not in value):
            raise ValueError("document requires title, sections, code and summary")
        return value


class MindmapResult(ResourceBase):
    mindmap: str

    @field_validator("mindmap")
    @classmethod
    def valid_mindmap(cls, value):
        if not value.strip().startswith("mindmap"):
            raise ValueError("invalid Mermaid mindmap")
        return value


class QuizQuestion(BaseModel):
    question: str
    options: Annotated[list[str], Field(min_length=2)]
    answer: str
    explanation: str
    difficulty: int = Field(ge=1, le=5)

    @model_validator(mode="after")
    def answer_is_an_option(self):
        if self.answer not in self.options:
            raise ValueError("answer must match an option")
        return self


class QuizResult(ResourceBase):
    questions: Annotated[list[QuizQuestion], Field(min_length=5, max_length=10)]


class VideoScene(BaseModel):
    shot: int = Field(ge=1)
    visual: str
    narration: str
    duration_seconds: int = Field(gt=0)
    bgm: str


class VideoScriptResult(ResourceBase):
    scenes: Annotated[list[VideoScene], Field(min_length=1)]


class CodeCaseResult(ResourceBase):
    language: Literal["python", "Python"]
    code: str
    input: str
    output: str
    complexity: str

    @field_validator("code")
    @classmethod
    def commented_python(cls, value):
        if "#" not in value:
            raise ValueError("Python code requires comments")
        return value


class ResourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_type: Literal["document", "mindmap", "quiz", "video_script", "code_case"]
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    rendered_html: str = ""
    metadata: dict = Field(default_factory=dict)


class ResourcePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    metadata: dict | None = None


class GenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    course: str = Field(min_length=1, max_length=100)
    profile: dict = Field(default_factory=dict)


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resource_type: str
    title: str
    content: str
    rendered_html: str = ""
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_json")


class ResourcePage(BaseModel):
    resources: list[ResourceResponse]
    total: int

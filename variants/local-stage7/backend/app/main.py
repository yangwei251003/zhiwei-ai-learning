from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.orchestrator import AgentDependencies, build_agent_graph
from app.agents.status import AgentStatusRegistry
from app.api.achievements import router as achievements_router
from app.api.admin import router as admin_router
from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.knowledge import router as knowledge_router
from app.api.path import router as path_router
from app.api.resources import router as resources_router
from app.core.config import Settings, get_settings
from app.core.database import Base, build_engine, build_session_factory
from app.core.llm import SparkAPIError, get_llm
from app.creative.vector_store import FaissVectorStore, SentenceTransformerEmbedder
from app.creative.achievements import AchievementService
from app.services.agent_storage import (
    ConversationStore,
    PathStore,
    ProfileStore,
    ResourceStore,
)
from app.services.knowledge import KnowledgeService
from app.services.paths import PathService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = build_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.state.vector_store = FaissVectorStore(
        settings.faiss_index_path,
        SentenceTransformerEmbedder(
            settings.embedding_model, dimension=settings.embedding_dimension
        ),
    )
    app.state.knowledge_service = KnowledgeService(
        app.state.session_factory,
        app.state.vector_store,
        settings.knowledge_upload_dir,
        score_threshold=settings.retrieval_score_threshold,
    )
    app.state.conversations = ConversationStore(app.state.session_factory)
    app.state.achievements = AchievementService(app.state.session_factory)
    app.state.agent_status = AgentStatusRegistry()
    profiles = ProfileStore(app.state.session_factory)
    resources = ResourceStore(app.state.session_factory)
    app.state.path_store = PathStore(app.state.session_factory)
    app.state.path_service = PathService(
        app.state.knowledge_service,
        profiles,
        lambda level: get_llm(level, settings),
        app.state.path_store,
    )
    dependencies = AgentDependencies(
        knowledge=app.state.knowledge_service,
        profiles=profiles,
        llm_factory=lambda level: get_llm(level, settings),
        resources=resources,
        path_service=app.state.path_service,
        status=app.state.agent_status,
    )
    agent_graph = build_agent_graph(dependencies)
    app.state.agent_graph_builder = lambda: agent_graph
    if settings.auto_create_tables:
        Base.metadata.create_all(engine)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(achievements_router, prefix=settings.api_prefix)
    app.include_router(admin_router, prefix=settings.api_prefix)
    app.include_router(agents_router, prefix=settings.api_prefix)
    app.include_router(chat_router, prefix=settings.api_prefix)
    app.include_router(knowledge_router, prefix=settings.api_prefix)
    app.include_router(path_router, prefix=settings.api_prefix)
    app.include_router(resources_router, prefix=settings.api_prefix)

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "data": None, "message": str(exc.detail)},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "data": jsonable_encoder(exc.errors()),
                "message": "请求参数验证失败",
            },
        )

    @app.exception_handler(SparkAPIError)
    async def spark_error(_: Request, exc: SparkAPIError) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"code": 503, "data": None, "message": str(exc)}
        )

    @app.get("/api/health")
    def health() -> dict:
        return {"code": 200, "data": {"status": "ok"}, "message": "ok"}

    return app


app = create_app()

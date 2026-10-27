from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core import get_settings
from app.api import achievements, agents, auth, challenges, chat, graph, knowledge, path, profile, resources

settings = get_settings()
default_cors_origins = ["http://localhost:5173", "http://localhost:3000"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if knowledge.get_knowledge_service.cache_info().currsize:
        knowledge.get_knowledge_service().close()
        knowledge.get_knowledge_service.cache_clear()

app = FastAPI(
    title="A3 多智能体学习系统",
    description="第十五届中国软件杯 A3 赛道 - 个性化资源生成与学习多智能体系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or default_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api/chat", tags=["对话"])
app.include_router(agents.router, prefix="/api/agents", tags=["智能体"])
app.include_router(resources.router, prefix="/api/resources", tags=["学习资源"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(profile.router, prefix="/api/profile", tags=["学习画像"])
app.include_router(path.router, prefix="/api/path", tags=["学习路径"])
app.include_router(graph.router, prefix="/api/graph", tags=["知识图谱"])
app.include_router(achievements.router, prefix="/api/achievements", tags=["成就"])
app.include_router(challenges.router, prefix="/api/challenges", tags=["挑战"])


@app.get("/")
def root():
    return {"message": "A3 多智能体学习系统 API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "llm": "讯飞星火 Spark API"}

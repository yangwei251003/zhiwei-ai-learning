from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas.creative import GraphEdgeIn, GraphNodeIn, GraphRebuildIn
from app.services.achievement_service import AchievementService
from app.services.graph_service import GraphConflictError, GraphCycleError, GraphNotFound, GraphService

router = APIRouter()
def service(db=Depends(get_db)): return GraphService(db, achievement_service=AchievementService(db))
@router.get("/{course}")
def graph(course: str, user: User=Depends(get_current_user), svc=Depends(service)): return svc.format_graph(user.id, course)
@router.post("/{course}/nodes")
def node(course: str, body: GraphNodeIn, user: User=Depends(get_current_user), svc=Depends(service)): return svc.upsert_node(user.id, course, body.model_dump())
@router.delete("/{course}/nodes/{node_id}", status_code=204)
def delete_node(course: str, node_id: int, user: User=Depends(get_current_user), svc=Depends(service)):
    try: svc.delete_node(user.id, course, node_id); return Response(status_code=204)
    except GraphNotFound: raise HTTPException(404, "知识点不存在")
@router.post("/{course}/edges")
def edge(course: str, body: GraphEdgeIn, user: User=Depends(get_current_user), svc=Depends(service)):
    try: return svc.upsert_edge(user.id, course, body.source, body.target, body.relation, body.weight, body.metadata_json)
    except GraphNotFound: raise HTTPException(404, "知识点不存在")
    except GraphCycleError: raise HTTPException(422, "前置关系不能成环")
    except GraphConflictError: raise HTTPException(409, "图谱已并发更新")
@router.delete("/{course}/edges/{edge_id}", status_code=204)
def delete_edge(course: str, edge_id: int, user: User=Depends(get_current_user), svc=Depends(service)):
    try: svc.delete_edge(user.id, course, edge_id); return Response(status_code=204)
    except GraphNotFound: raise HTTPException(404, "关系不存在")
@router.post("/{course}/rebuild")
def rebuild(course: str, body: GraphRebuildIn, user: User=Depends(get_current_user), svc=Depends(service)):
    try: return svc.rebuild(user.id, course, body.model_dump())
    except (GraphCycleError, KeyError): raise HTTPException(422, "图谱结构无效")

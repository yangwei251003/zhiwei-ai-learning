import threading
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import KnowledgeGraphEdge, KnowledgeGraphNode

RELATIONS = {"prerequisite", "related", "applied_by"}


class GraphNotFound(LookupError): pass
class GraphCycleError(ValueError): pass
class GraphConflictError(RuntimeError): pass
class InvalidRelation(ValueError): pass

_lock_guard = threading.Lock()
_locks = {}
def _tenant_lock(user_id, course):
    key = (user_id, course)
    with _lock_guard:
        return _locks.setdefault(key, threading.RLock())


class GraphService:
    def __init__(self, db: Session, concept_extractor=None, achievement_service=None):
        self.db, self.concept_extractor, self.achievement_service = db, concept_extractor, achievement_service

    def get_node(self, user_id, course, node_id):
        node = self.db.query(KnowledgeGraphNode).filter_by(id=node_id, user_id=user_id, course=course).first()
        if not node: raise GraphNotFound("node not found")
        return node

    def upsert_node(self, user_id, course, data):
        with _tenant_lock(user_id, course):
            node = self.db.query(KnowledgeGraphNode).filter_by(user_id=user_id, course=course, key=data["key"]).first()
            if node is None:
                node = KnowledgeGraphNode(user_id=user_id, course=course, key=data["key"], label=data.get("label", data["key"]))
                self.db.add(node)
            for name in ("label", "difficulty", "mastery", "status", "resource_ids", "metadata_json"):
                if name in data: setattr(node, name, data[name])
            try: self.db.commit()
            except IntegrityError:
                self.db.rollback(); node = self.db.query(KnowledgeGraphNode).filter_by(user_id=user_id, course=course, key=data["key"]).one()
            self.db.refresh(node)
            if self.achievement_service:
                mastered = self.db.query(KnowledgeGraphNode).filter_by(user_id=user_id, course=course).filter(KnowledgeGraphNode.mastery >= 1).count()
                self.achievement_service.evaluate(user_id, "graph_mastery_updated", {"mastered_nodes": mastered})
            return node

    def delete_node(self, user_id, course, node_id):
        node = self.get_node(user_id, course, node_id)
        self.db.query(KnowledgeGraphEdge).filter_by(user_id=user_id, course=course).filter(
            (KnowledgeGraphEdge.source_node_id == node_id) | (KnowledgeGraphEdge.target_node_id == node_id)).delete(synchronize_session=False)
        self.db.delete(node); self.db.commit()

    def _would_cycle(self, user_id, course, source, target):
        adjacency = {}
        for edge in self.db.query(KnowledgeGraphEdge).filter_by(user_id=user_id, course=course, relation="prerequisite"):
            adjacency.setdefault(edge.source_node_id, set()).add(edge.target_node_id)
        stack, seen = [target], set()
        while stack:
            current = stack.pop()
            if current == source: return True
            if current not in seen:
                seen.add(current); stack.extend(adjacency.get(current, ()))
        return False

    def upsert_edge(self, user_id, course, source, target, relation, weight=1.0, metadata_json=None):
        with _tenant_lock(user_id, course):
            if relation not in RELATIONS: raise InvalidRelation(relation)
            self.get_node(user_id, course, source); self.get_node(user_id, course, target)
            edge = self.db.query(KnowledgeGraphEdge).filter_by(source_node_id=source, target_node_id=target, relation=relation).first()
            if edge and (edge.user_id != user_id or edge.course != course): raise GraphNotFound("edge not found")
            if relation == "prerequisite" and (source == target or (edge is None and self._would_cycle(user_id, course, source, target))): raise GraphCycleError("prerequisite cycle")
            if edge is None:
                edge = KnowledgeGraphEdge(user_id=user_id, course=course, source_node_id=source, target_node_id=target, relation=relation)
                self.db.add(edge)
            edge.weight, edge.metadata_json = weight, metadata_json or {}
            try: self.db.commit()
            except IntegrityError:
                self.db.rollback()
                edge = self.db.query(KnowledgeGraphEdge).filter_by(user_id=user_id, course=course, source_node_id=source, target_node_id=target, relation=relation).first()
                if edge is None: raise GraphConflictError("graph changed concurrently")
            self.db.refresh(edge); return edge

    def delete_edge(self, user_id, course, edge_id):
        edge = self.db.query(KnowledgeGraphEdge).filter_by(id=edge_id, user_id=user_id, course=course).first()
        if not edge: raise GraphNotFound("edge not found")
        self.db.delete(edge); self.db.commit()

    def rebuild(self, user_id, course, concepts=None, source=None):
        payload = concepts if concepts is not None else self.concept_extractor(source)
        nodes = {x["key"]: self.upsert_node(user_id, course, x) for x in payload.get("nodes", [])}
        for edge in payload.get("edges", []):
            self.upsert_edge(user_id, course, nodes[edge["source"]].id, nodes[edge["target"]].id, edge["relation"], edge.get("weight", 1))
        return self.format_graph(user_id, course)

    def format_graph(self, user_id, course):
        nodes = self.db.query(KnowledgeGraphNode).filter_by(user_id=user_id, course=course).all()
        edges = self.db.query(KnowledgeGraphEdge).filter_by(user_id=user_id, course=course).all()
        return {"nodes": [{"id": n.id, "key": n.key, "label": n.label, "difficulty": n.difficulty, "mastery": n.mastery, "status": n.status, "resource_ids": n.resource_ids, "metadata": n.metadata_json} for n in nodes],
                "edges": [{"id": e.id, "source": e.source_node_id, "target": e.target_node_id, "relation": e.relation, "weight": e.weight, "metadata": e.metadata_json} for e in edges]}

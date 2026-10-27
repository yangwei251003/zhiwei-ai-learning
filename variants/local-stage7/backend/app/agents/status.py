from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from threading import RLock
from time import perf_counter


AGENT_LABELS = {
    "retriever": "知识检索",
    "profile_agent": "学生画像",
    "intent_classifier": "意图识别",
    "resource_agent": "资源生成",
    "path_agent": "路径规划",
    "tutor_agent": "智能辅导",
    "general_agent": "常规对话",
    "response_agent": "响应汇总",
}


@dataclass
class AgentRuntimeStatus:
    status: str = "idle"
    run_count: int = 0
    last_duration_ms: float | None = None
    enabled: bool = True


class AgentStatusRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._statuses = {name: AgentRuntimeStatus() for name in AGENT_LABELS}

    @asynccontextmanager
    async def track(self, name: str):
        started = perf_counter()
        with self._lock:
            status = self._statuses[name]
            status.status = "running"
            status.run_count += 1
        try:
            yield
        finally:
            with self._lock:
                status.status = "idle"
                status.last_duration_ms = round((perf_counter() - started) * 1000, 2)

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name in self._statuses:
            with self._lock:
                self._statuses[name].enabled = enabled

    def is_enabled(self, name: str) -> bool:
        with self._lock:
            return self._statuses.get(name, AgentRuntimeStatus(enabled=False)).enabled

    def snapshot(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "name": name,
                    "label": AGENT_LABELS[name],
                    "status": status.status,
                    "run_count": status.run_count,
                    "last_duration_ms": status.last_duration_ms,
                    "enabled": status.enabled,
                }
                for name, status in self._statuses.items()
            ]

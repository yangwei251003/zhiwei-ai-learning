from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from app.agents.state import AgentEvent, AgentState, Intent


VALID_INTENTS = {"profile", "resource", "path", "tutor", "chat"}


def event(event_type: str, payload: dict[str, Any] | None = None) -> AgentEvent:
    return {"type": event_type, "payload": payload or {}}


def normalize_event(raw: dict[str, Any]) -> AgentEvent:
    if "payload" in raw:
        payload = raw["payload"]
    elif "content" in raw:
        payload = {"content": raw["content"]}
    else:
        payload = raw.get("data", {})
    if not isinstance(payload, dict):
        payload = {"value": payload}
    return event(str(raw.get("type", "event")), payload)


def make_memory_node(loader: Callable[[AgentState], Awaitable[dict[str, Any]]]):
    async def memory_node(state: AgentState) -> dict[str, Any]:
        context = await loader(state)
        return {
            "history": context.get("history", []),
            "profile": context.get("profile", {}),
            "events": [event("memory_loaded", {
                "history_count": len(context.get("history", [])),
                "has_profile": bool(context.get("profile")),
            })],
        }
    return memory_node


def make_intent_classifier(llm: Any):
    async def intent_classifier(state: AgentState) -> dict[str, Any]:
        prompt = (
            "Classify the student message. Return exactly one lowercase word: "
            "profile, resource, path, tutor, or chat.\n"
            f"Message: {state['message']}"
        )
        answer = (await llm.complete(prompt)).strip().lower()
        intent: Intent = answer if answer in VALID_INTENTS else "chat"
        return {"intent": intent, "events": [event("intent_classified", {"intent": intent})]}
    return intent_classifier


def make_agent_node(name: str, agent: Any):
    async def agent_node(state: AgentState) -> dict[str, Any]:
        raw_events = await agent.run(state)
        if hasattr(raw_events, "__aiter__"):
            raw_events = [item async for item in raw_events]
        events = [normalize_event(item) for item in raw_events]
        resources = [item["payload"] for item in events if item["type"] == "resource"]
        path_events = [item["payload"] for item in events if item["type"] == "path_created"]
        return {
            "events": [event("agent_selected", {"agent": name}), *events],
            "resources": resources,
            "path": path_events[-1] if path_events else state.get("path"),
        }
    agent_node.__name__ = name
    return agent_node


async def response_agent(state: AgentState) -> dict[str, Any]:
    texts = [item["payload"].get("content", "") for item in state.get("events", [])
             if item["type"] == "text"]
    response = "".join(texts)
    return {"response_text": response, "events": [event("response_ready", {"content": response})]}


def route_intent(state: AgentState) -> str:
    if state["intent"] == "chat":
        return "tutor_agent"
    return f"{state['intent']}_agent"

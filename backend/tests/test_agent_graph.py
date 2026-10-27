import inspect

import pytest
import asyncio

from app.agents.graph import AgentDependencies, build_agent_graph
from app.agents.orchestrator import AgentOrchestrator


class FakeLLM:
    def __init__(self, intent):
        self.intent = intent
        self.prompts = []

    async def complete(self, prompt):
        assert isinstance(prompt, str)
        self.prompts.append(prompt)
        return self.intent

    def is_connected(self):
        return True


class FakeAgent:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    async def run(self, state):
        self.calls.append((self.name, state["message"], state["profile"]))
        return [{"type": "text", "payload": {"content": self.name}}]


def dependencies(intent, calls):
    async def load_memory(state):
        return {
            "history": [{"role": "user", "content": "earlier"}],
            "profile": {"goal": "pass"},
        }

    return AgentDependencies(
        llm=FakeLLM(intent),
        memory_loader=load_memory,
        profile_agent=FakeAgent("profile_agent", calls),
        resource_agent=FakeAgent("resource_agent", calls),
        path_agent=FakeAgent("path_agent", calls),
        tutor_agent=FakeAgent("tutor_agent", calls),
    )


def test_graph_contains_required_topology():
    graph = build_agent_graph(dependencies("chat", []))
    view = graph.get_graph()
    nodes = set(view.nodes)
    assert {
        "memory_node", "intent_classifier", "profile_agent", "resource_agent",
        "path_agent", "tutor_agent", "response_agent",
    } <= nodes
    edges = {(edge.source, edge.target) for edge in view.edges}
    assert ("__start__", "memory_node") in edges
    assert ("memory_node", "intent_classifier") in edges
    for agent in ("profile_agent", "resource_agent", "path_agent", "tutor_agent"):
        assert (agent, "response_agent") in edges
    assert ("response_agent", "__end__") in edges


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("intent", "selected"),
    [("profile", "profile_agent"), ("resource", "resource_agent"),
     ("path", "path_agent"), ("tutor", "tutor_agent"),
     ("chat", "tutor_agent")],
)
async def test_each_intent_selects_exactly_one_agent_and_passes_context(intent, selected):
    calls = []
    result = await build_agent_graph(dependencies(intent, calls)).ainvoke({
        "user_id": 7, "conversation_id": "c1", "message": "help",
        "course": "AI", "events": [], "errors": [],
    })
    assert calls == [(selected, "help", {"goal": "pass"})]
    assert result["history"][0]["content"] == "earlier"
    assert result["intent"] == intent
    assert result["response_text"] == selected
    assert all(set(event) == {"type", "payload"} for event in result["events"])


def test_orchestrator_is_a_thin_graph_adapter():
    source = inspect.getsource(AgentOrchestrator)
    assert "SparkLLM" not in source
    assert "if intent" not in source
    assert ".ainvoke(" in source
    assert ".astream(" in source


@pytest.mark.asyncio
async def test_default_tutor_streams_first_token_before_completion_and_receives_context():
    released = asyncio.Event()

    class StreamingLLM(FakeLLM):
        async def complete(self, prompt):
            if "Classify" in prompt:
                return "chat"
            raise AssertionError("tutor must stream")

        async def stream(self, prompt):
            self.prompts.append(prompt)
            yield "first"
            await released.wait()
            yield "second"

    llm = StreamingLLM("chat")
    tutor = __import__("app.agents.tutor_agent", fromlist=["TutorAgent"]).TutorAgent(llm, 1, None)
    state = {
        "message": "help", "course": "AI",
        "history": [{"role": "user", "content": "earlier"}],
        "profile": {"goal": "pass"},
        "rag_chunks": [{"content": "retrieved fact"}],
    }
    stream = tutor.run(state)
    first = await anext(stream)
    assert first == {"type": "token", "payload": {"content": "first"}}
    assert "earlier" in llm.prompts[-1]
    assert "pass" in llm.prompts[-1]
    assert "retrieved fact" in llm.prompts[-1]
    released.set()
    assert (await anext(stream))["payload"]["content"] == "second"

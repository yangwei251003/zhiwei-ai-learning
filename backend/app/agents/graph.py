from dataclasses import dataclass
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    make_agent_node, make_intent_classifier, make_memory_node, response_agent, route_intent,
)
from app.agents.state import AgentState


@dataclass
class AgentDependencies:
    llm: Any
    memory_loader: Any
    profile_agent: Any
    resource_agent: Any
    path_agent: Any
    tutor_agent: Any


def build_agent_graph(dependencies: AgentDependencies):
    builder = StateGraph(AgentState)
    builder.add_node("memory_node", make_memory_node(dependencies.memory_loader))
    builder.add_node("intent_classifier", make_intent_classifier(dependencies.llm))
    for name in ("profile_agent", "resource_agent", "path_agent", "tutor_agent"):
        builder.add_node(name, make_agent_node(name, getattr(dependencies, name)))
    builder.add_node("response_agent", response_agent)
    builder.add_edge(START, "memory_node")
    builder.add_edge("memory_node", "intent_classifier")
    builder.add_conditional_edges("intent_classifier", route_intent, {
        name: name for name in ("profile_agent", "resource_agent", "path_agent", "tutor_agent")
    })
    for name in ("profile_agent", "resource_agent", "path_agent", "tutor_agent"):
        builder.add_edge(name, "response_agent")
    builder.add_edge("response_agent", END)
    return builder.compile()

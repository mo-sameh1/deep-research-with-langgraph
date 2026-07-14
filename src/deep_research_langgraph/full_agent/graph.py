"""Graph assembly for the full deep-research agent."""

from __future__ import annotations

from typing import Literal, cast

from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import SecretStr

from deep_research_langgraph.models import get_chat_model
from deep_research_langgraph.research.types import ChatModelLike as ResearchChatModelLike
from deep_research_langgraph.research_supervisor.graph import (
    build_supervisor_graph,
)
from deep_research_langgraph.research_supervisor.nodes import (
    GraphResearchAgentRunner,
    SupervisorServices,
)
from deep_research_langgraph.research_supervisor.types import SupervisorModelLike
from deep_research_langgraph.scope.graph import create_default_scope_services
from deep_research_langgraph.scope.nodes import (
    ClarifyWithUserNode,
    ScopeServices,
    WriteResearchBriefNode,
)
from deep_research_langgraph.scope.types import ChatModelLike as ScopeChatModelLike
from deep_research_langgraph.settings import Settings, get_settings

from .nodes import FinalReportGenerationNode, FullAgentServices
from .types import FullAgentInputState, FullAgentState, WriterModelLike

ModelProvider = Literal["ollama", "groq"]


def build_full_agent_graph(
    *,
    scope_services: ScopeServices,
    supervisor_services: SupervisorServices,
    full_agent_services: FullAgentServices,
) -> CompiledStateGraph:
    """Build the course-style full deep-research graph."""

    builder = StateGraph(FullAgentState, input_schema=FullAgentInputState)
    builder.add_node("clarify_with_user", ClarifyWithUserNode(scope_services))
    builder.add_node("write_research_brief", WriteResearchBriefNode(scope_services))
    builder.add_node("supervisor_subgraph", build_supervisor_graph(supervisor_services))
    builder.add_node("final_report_generation", FinalReportGenerationNode(full_agent_services))

    builder.add_edge(START, "clarify_with_user")
    builder.add_edge("write_research_brief", "supervisor_subgraph")
    builder.add_edge("supervisor_subgraph", "final_report_generation")
    builder.add_edge("final_report_generation", END)

    return builder.compile()


def create_default_full_agent_services(
    *,
    writer_model: WriterModelLike | None = None,
    model_provider: str | None = None,
) -> FullAgentServices:
    """Create services for the final report generation step."""

    settings = get_settings()
    provider = _resolve_model_provider(model_provider, settings)
    return FullAgentServices(
        writer_llm=writer_model or _get_writer_model(provider=provider, settings=settings)
    )


def create_default_full_agent_app(
    *,
    model_provider: str | None = None,
) -> CompiledStateGraph:
    """Create a runnable full deep-research graph."""

    settings = get_settings()
    provider = _resolve_model_provider(model_provider, settings)
    shared_model = _get_shared_model(provider=provider, settings=settings)
    scope_services = create_default_scope_services(
        model=cast(ScopeChatModelLike, shared_model),
    )
    supervisor_services = SupervisorServices(
        llm=cast(SupervisorModelLike, shared_model),
        research_runner=GraphResearchAgentRunner(model=cast(ResearchChatModelLike, shared_model)),
    )
    return build_full_agent_graph(
        scope_services=scope_services,
        supervisor_services=supervisor_services,
        full_agent_services=create_default_full_agent_services(model_provider=provider),
    )


def _resolve_model_provider(
    model_provider: str | None,
    settings: Settings,
) -> ModelProvider:
    provider = model_provider or settings.full_agent_model_provider
    if provider not in {"ollama", "groq"}:
        msg = "model_provider must be either 'ollama' or 'groq'."
        raise ValueError(msg)
    if provider == "groq" and not settings.groq_api_key:
        msg = "GROQ_API_KEY is required when using --model-provider groq."
        raise ValueError(msg)
    return cast(ModelProvider, provider)


def _get_shared_model(*, provider: ModelProvider, settings: Settings) -> object:
    if provider == "groq":
        return ChatGroq(
            model=settings.groq_model,
            api_key=_get_groq_api_key(settings),
            temperature=settings.ollama_temperature,
            max_tokens=settings.groq_max_tokens,
        )
    return get_chat_model()


def _get_writer_model(*, provider: ModelProvider, settings: Settings) -> WriterModelLike:
    if provider == "groq":
        return cast(
            WriterModelLike,
            ChatGroq(
                model=settings.groq_model,
                api_key=_get_groq_api_key(settings),
                temperature=settings.ollama_temperature,
                max_tokens=settings.groq_max_tokens,
            ),
        )
    return cast(
        WriterModelLike,
        ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            num_ctx=settings.ollama_num_ctx,
            num_predict=settings.ollama_writer_num_predict,
            temperature=settings.ollama_temperature,
            validate_model_on_init=True,
        ),
    )


def _get_groq_api_key(settings: Settings) -> SecretStr:
    if settings.groq_api_key is None:
        msg = "GROQ_API_KEY is required when using --model-provider groq."
        raise ValueError(msg)
    return SecretStr(settings.groq_api_key)


__all__ = [
    "build_full_agent_graph",
    "create_default_full_agent_app",
    "create_default_full_agent_services",
]

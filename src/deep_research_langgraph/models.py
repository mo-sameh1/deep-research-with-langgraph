"""Model factories shared by course notebooks and applications."""

from langchain_ollama import ChatOllama

from deep_research_langgraph.settings import get_settings


def get_chat_model() -> ChatOllama:
    """Build the configured local Ollama chat model without invoking it."""

    settings = get_settings()
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        num_ctx=settings.ollama_num_ctx,
        temperature=settings.ollama_temperature,
        validate_model_on_init=True,
    )

"""Environment-backed settings for local model access."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Course settings loaded from environment variables or a local `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "langgraph-coder"
    ollama_num_ctx: int = Field(default=32768, ge=4096)
    ollama_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    ollama_writer_num_predict: int = Field(default=512, ge=128)
    full_agent_model_provider: Literal["ollama", "groq"] = "ollama"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_max_tokens: int = Field(default=2048, ge=128)
    langsmith_tracing: bool = False
    langchain_tracing_v2: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "deep-research-with-langgraph"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_workspace_id: str | None = None
    tavily_api_key: str | None = None
    tavily_search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic"
    tavily_include_answer: bool = False
    tavily_include_raw_content: bool = False
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    @field_validator(
        "langsmith_api_key",
        "langsmith_workspace_id",
        "tavily_api_key",
        "groq_api_key",
        "openai_api_key",
        "anthropic_api_key",
        mode="before",
    )
    @classmethod
    def normalize_blank_secret(cls, value: object) -> object:
        """Treat blank optional secret values as unset."""

        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()

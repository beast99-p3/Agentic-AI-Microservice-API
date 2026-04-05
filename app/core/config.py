from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="agentic-ai-microservice-api", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    llm_provider: str = Field(default="openai_compatible", alias="LLM_PROVIDER")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    llm_api_key: str = Field(
        default="",
        alias="LLM_API_KEY",
        validation_alias=AliasChoices("GEMINI_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"),
    )
    llm_default_model: str = Field(default="models/gemini-2.5-flash", alias="LLM_DEFAULT_MODEL")
    llm_default_temperature: float = Field(default=0.2, alias="LLM_DEFAULT_TEMPERATURE")
    llm_timeout_seconds: int = Field(default=30, alias="LLM_TIMEOUT_SECONDS")

    default_max_steps: int = Field(default=8, alias="DEFAULT_MAX_STEPS")
    default_max_tool_calls: int = Field(default=12, alias="DEFAULT_MAX_TOOL_CALLS")
    default_max_runtime_seconds: int = Field(default=45, alias="DEFAULT_MAX_RUNTIME_SECONDS")
    tool_timeout_seconds: int = Field(default=6, alias="TOOL_TIMEOUT_SECONDS")
    repeated_tool_call_threshold: int = Field(default=2, alias="REPEATED_TOOL_CALL_THRESHOLD")

    enable_stream_endpoint: bool = Field(default=True, alias="ENABLE_STREAM_ENDPOINT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @computed_field
    @property
    def parsed_allowed_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        return origins or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

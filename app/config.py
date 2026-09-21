"""ChroniQ MCP Server Configuration.

All settings are loaded from environment variables or a .env file.
Secrets must never be hard-coded.
"""

from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated environment settings for the ChroniQ MCP server."""

    # ChroniQ backend connection
    chroniq_api_base_url: str = "http://127.0.0.1:8000"
    chroniq_request_timeout: float = Field(default=15.0, gt=0)
    chroniq_connect_timeout: float = Field(default=5.0, gt=0)

    # MCP transport configuration
    mcp_host: str = "0.0.0.0"
    mcp_port: int = Field(
        default=8001,
        ge=1,
        le=65535,
        validation_alias=AliasChoices("mcp_port", "port"),
    )
    mcp_transport: Literal["streamable-http", "sse", "stdio"] = "streamable-http"
    mcp_path: str = "/mcp"

    # Safety gate — mutations disabled by default
    chroniq_enable_mutations: bool = False

    # Dev-only: single-patient bearer token for local testing fallback.
    # NEVER use a shared admin/super-admin token. NEVER use in production.
    chroniq_auth_token: str = ""

    @field_validator("chroniq_api_base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("CHRONIQ_API_BASE_URL must begin with http:// or https://")
        return v.rstrip("/")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


"""ChroniQ MCP Server Configuration.

All settings are loaded from environment variables or a .env file.
Secrets must never be hard-coded.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated environment settings for the ChroniQ MCP server."""

    # ChroniQ backend connection
    chroniq_api_base_url: str = "http://127.0.0.1:8000"
    chroniq_request_timeout: float = 15.0
    chroniq_connect_timeout: float = 5.0

    # MCP transport
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8001

    # Safety gate — mutations disabled by default
    chroniq_enable_mutations: bool = False

    # Dev-only: single-patient bearer token for local testing.
    # NEVER use a shared admin/super-admin token.  NEVER use in production.
    chroniq_auth_token: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

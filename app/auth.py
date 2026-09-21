"""Caller identity context for bearer-token forwarding.

The bearer token is set by the MCP transport / session layer and read
by the HTTP client.  It must NEVER be accepted from ordinary tool arguments.
"""

from contextvars import ContextVar

from app.config import settings

# Set only from a trusted transport authentication layer, never from tool arguments.
_caller_bearer_token: ContextVar[str | None] = ContextVar(
    "_caller_bearer_token", default=None
)


def set_caller_bearer_token(token: str | None) -> None:
    """Set the caller's bearer token for the current async context."""
    _caller_bearer_token.set(token)


def get_caller_bearer_token() -> str | None:
    """Return the caller's bearer token.

    Priority:
      1. Per-request ContextVar (set by transport/session layer)
      2. CHRONIQ_AUTH_TOKEN env var (dev-only fallback)
    """
    token = _caller_bearer_token.get()
    if token:
        return token
    # Fallback to env var for single-patient dev usage
    if settings.chroniq_auth_token:
        return settings.chroniq_auth_token
    return None

"""Shared test fixtures for ChroniQ MCP tests.

All tests use mocked HTTP responses — no production credentials or
real patient data required.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.auth import set_caller_bearer_token, _caller_bearer_token
from app.config import Settings


@pytest.fixture(autouse=True)
def _reset_bearer_token():
    """Reset the bearer token context var before each test."""
    set_caller_bearer_token(None)
    yield
    set_caller_bearer_token(None)


@pytest.fixture
def mock_settings(monkeypatch):
    """Return a factory that patches settings values."""
    def _patch(**overrides):
        for key, value in overrides.items():
            monkeypatch.setattr(f"app.config.settings.{key}", value)
    return _patch


@pytest.fixture
def auth_token():
    """Set a fake patient bearer token for testing."""
    token = "test-patient-jwt-token-abc123"
    set_caller_bearer_token(token)
    return token


@pytest.fixture
def mock_api():
    """Return an activated respx mock router."""
    with respx.mock(base_url="http://127.0.0.1:8000", assert_all_called=False) as router:
        yield router


def json_response(data, status_code: int = 200) -> Response:
    """Create an httpx.Response with JSON body."""
    return Response(status_code, json=data)


def error_response(status_code: int, detail: str = "Error") -> Response:
    """Create an httpx.Response for an error."""
    return Response(status_code, json={"detail": detail})

"""Tests for app.auth — bearer token context management."""

import pytest
from app.auth import get_caller_bearer_token, set_caller_bearer_token


class TestAuth:
    def test_default_token_is_none(self):
        assert get_caller_bearer_token() is None

    def test_set_and_get_token(self):
        set_caller_bearer_token("test-token-123")
        assert get_caller_bearer_token() == "test-token-123"

    def test_clear_token(self):
        set_caller_bearer_token("some-token")
        set_caller_bearer_token(None)
        # Falls back to env var; with empty default, returns None
        # (assuming CHRONIQ_AUTH_TOKEN is empty in test env)

    def test_env_fallback(self, mock_settings):
        """When no context token is set, falls back to CHRONIQ_AUTH_TOKEN."""
        set_caller_bearer_token(None)
        mock_settings(chroniq_auth_token="env-dev-token")
        assert get_caller_bearer_token() == "env-dev-token"

    def test_context_token_overrides_env(self, mock_settings):
        """ContextVar token takes priority over env var."""
        mock_settings(chroniq_auth_token="env-dev-token")
        set_caller_bearer_token("session-token")
        assert get_caller_bearer_token() == "session-token"

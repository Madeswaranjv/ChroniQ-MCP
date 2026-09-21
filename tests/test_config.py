"""Tests for app.config — environment configuration and defaults."""

import pytest
from app.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings(
            _env_file=None,
            chroniq_api_base_url="http://localhost:8000",
        )
        assert s.chroniq_api_base_url == "http://localhost:8000"
        assert s.chroniq_enable_mutations is False
        assert s.mcp_host == "127.0.0.1"
        assert s.mcp_port == 8001
        assert s.chroniq_request_timeout == 15.0
        assert s.chroniq_connect_timeout == 5.0
        assert s.chroniq_auth_token == ""

    def test_mutations_default_disabled(self):
        s = Settings(_env_file=None)
        assert s.chroniq_enable_mutations is False

    def test_mutations_can_be_enabled(self):
        s = Settings(_env_file=None, chroniq_enable_mutations=True)
        assert s.chroniq_enable_mutations is True

    def test_auth_token_default_empty(self):
        s = Settings(_env_file=None)
        assert s.chroniq_auth_token == ""

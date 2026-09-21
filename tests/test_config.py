"""Tests for app.config — environment configuration, validation, and defaults."""

import pytest
from pydantic import ValidationError

from app.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings(
            _env_file=None,
            chroniq_api_base_url="http://localhost:8000",
        )
        assert s.chroniq_api_base_url == "http://localhost:8000"
        assert s.chroniq_enable_mutations is False
        assert s.mcp_host == "0.0.0.0"
        assert s.mcp_port == 8001
        assert s.mcp_transport == "streamable-http"
        assert s.mcp_path == "/mcp"
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

    def test_port_alias_support(self, monkeypatch):
        monkeypatch.setenv("PORT", "10000")
        monkeypatch.delenv("MCP_PORT", raising=False)
        s = Settings(_env_file=None)
        assert s.mcp_port == 10000

    def test_invalid_base_url_rejected(self):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, chroniq_api_base_url="ftp://invalid.example.com")

    def test_non_positive_timeout_rejected(self):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, chroniq_request_timeout=0.0)

        with pytest.raises(ValidationError):
            Settings(_env_file=None, chroniq_connect_timeout=-5.0)

    def test_invalid_port_range_rejected(self):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, mcp_port=0)

        with pytest.raises(ValidationError):
            Settings(_env_file=None, mcp_port=70000)

    def test_invalid_transport_rejected(self):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, mcp_transport="grpc")

"""Tests for patient profile tools."""

import pytest
from httpx import Response

from app.tools.patient import get_patient_profile, update_patient_profile


class TestGetPatientProfile:
    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token):
        mock_api.get("/patients/me/profile").mock(
            return_value=Response(200, json={"id": "u1", "name": "Alice", "role": "patient"})
        )
        result = await get_patient_profile()
        assert result["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_correct_route(self, mock_api, auth_token):
        mock_api.get("/patients/me/profile").mock(return_value=Response(200, json={}))
        await get_patient_profile()
        assert mock_api.calls[0].request.url.path == "/patients/me/profile"


class TestUpdatePatientProfile:
    @pytest.mark.asyncio
    async def test_mutations_disabled(self, mock_settings):
        mock_settings(chroniq_enable_mutations=False)
        result = await update_patient_profile(name="Bob")
        assert "Mutations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_no_fields_provided(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await update_patient_profile()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_sensitive_requires_confirmation(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await update_patient_profile(email="new@test.com")
        assert result["status"] == "confirmation_required"

    @pytest.mark.asyncio
    async def test_nonsensitive_no_confirmation(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.patch("/users/me").mock(
            return_value=Response(200, json={"id": "u1", "name": "Bob"})
        )
        result = await update_patient_profile(name="Bob")
        assert result["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_uses_correct_route(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.patch("/users/me").mock(return_value=Response(200, json={}))
        await update_patient_profile(name="Test")
        assert mock_api.calls[0].request.url.path == "/users/me"

"""Tests for account tools."""

import pytest
from httpx import Response

from app.tools.account import update_notification_preferences


class TestUpdateNotificationPreferences:
    @pytest.mark.asyncio
    async def test_mutations_disabled(self, mock_settings):
        mock_settings(chroniq_enable_mutations=False)
        result = await update_notification_preferences(reminder_24h=False)
        assert "Mutations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_no_fields(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await update_notification_preferences()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.put("/users/me/notification-preferences").mock(
            return_value=Response(200, json={"id": "u1", "notification_preferences": {}})
        )
        result = await update_notification_preferences(reminder_24h=False)
        assert "id" in result

    @pytest.mark.asyncio
    async def test_correct_route(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.put("/users/me/notification-preferences").mock(
            return_value=Response(200, json={})
        )
        await update_notification_preferences(reminder_1h=True)
        req = mock_api.calls[0].request
        assert req.url.path == "/users/me/notification-preferences"
        assert req.method == "PUT"

    @pytest.mark.asyncio
    async def test_channels_schema(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.put("/users/me/notification-preferences").mock(
            return_value=Response(200, json={})
        )
        await update_notification_preferences(
            channels={"booking_confirmed": {"in_app": True, "email": True, "sms": False}}
        )
        import json
        body = json.loads(mock_api.calls[0].request.content)
        assert body["channels"]["booking_confirmed"]["in_app"] is True

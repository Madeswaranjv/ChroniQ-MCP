"""Tests for notification tools."""

import pytest
from httpx import Response

from app.tools.notifications import list_notifications, mark_notification_as_read


class TestListNotifications:
    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token):
        mock_api.get("/notifications").mock(
            return_value=Response(200, json=[
                {"id": "n1", "title": "Reminder", "message": None, "body": "Your appointment"}
            ])
        )
        result = await list_notifications()
        assert result["count"] == 1
        # Verify body/message normalisation
        notif = result["notifications"][0]
        assert notif["message"] == "Your appointment"
        assert notif["body"] == "Your appointment"

    @pytest.mark.asyncio
    async def test_message_field_preferred(self, mock_api, auth_token):
        mock_api.get("/notifications").mock(
            return_value=Response(200, json=[
                {"id": "n1", "title": "Test", "message": "From message"}
            ])
        )
        result = await list_notifications()
        assert result["notifications"][0]["message"] == "From message"


class TestMarkNotificationAsRead:
    @pytest.mark.asyncio
    async def test_mutations_disabled(self, mock_settings):
        mock_settings(chroniq_enable_mutations=False)
        result = await mark_notification_as_read("n1")
        assert "Mutations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.patch("/notifications/n1/read").mock(
            return_value=Response(200, json={"success": True, "id": "n1", "read": True})
        )
        result = await mark_notification_as_read("n1")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_empty_id(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await mark_notification_as_read("")
        assert "error" in result

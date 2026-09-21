"""Tests for support ticket tools."""

import pytest
from httpx import Response

from app.tools.support import create_support_ticket, list_support_tickets


class TestListSupportTickets:
    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token):
        mock_api.get("/support/tickets").mock(
            return_value=Response(200, json=[{"id": "t1", "reference": "TICK-ABC"}])
        )
        result = await list_support_tickets()
        assert result["count"] == 1


class TestCreateSupportTicket:
    @pytest.mark.asyncio
    async def test_requires_confirmation(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await create_support_ticket("booking_problem", "Cannot book")
        assert result["status"] == "confirmation_required"

    @pytest.mark.asyncio
    async def test_invalid_category(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await create_support_ticket("invalid_cat", "desc")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_contact_preference(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await create_support_ticket(
            "booking_problem", "desc", contact_preference="whatsapp"
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_description(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await create_support_ticket("booking_problem", "")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_confirmed(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.post("/support/tickets").mock(
            return_value=Response(201, json={"id": "t1", "reference": "TICK-XYZ"})
        )
        result = await create_support_ticket(
            "app_problem", "App crashes", confirmed=True
        )
        assert result["reference"] == "TICK-XYZ"

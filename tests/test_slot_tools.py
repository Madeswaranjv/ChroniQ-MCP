"""Tests for slot tools — get_doctor_slots, hold, release."""

import pytest
from httpx import Response

from app.tools.slots import get_doctor_slots, hold_appointment_slot, release_appointment_slot


class TestGetDoctorSlots:
    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token):
        mock_api.get("/doctors/d1/slots").mock(
            return_value=Response(200, json=[{"id": "s1", "status": "open"}])
        )
        result = await get_doctor_slots("d1", "2026-09-22")
        assert result["count"] == 1
        assert result["doctor_id"] == "d1"

    @pytest.mark.asyncio
    async def test_invalid_date_format(self):
        result = await get_doctor_slots("d1", "22-09-2026")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_doctor_id(self):
        result = await get_doctor_slots("", "2026-09-22")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_correct_route_and_params(self, mock_api):
        mock_api.get("/doctors/doc123/slots").mock(return_value=Response(200, json=[]))
        await get_doctor_slots("doc123", "2026-10-01")
        req = mock_api.calls[0].request
        assert "date=2026-10-01" in str(req.url)


class TestHoldAppointmentSlot:
    @pytest.mark.asyncio
    async def test_mutations_disabled(self, mock_settings):
        mock_settings(chroniq_enable_mutations=False)
        result = await hold_appointment_slot("s1", confirmed=True)
        assert "Mutations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_confirmation(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await hold_appointment_slot("s1")
        assert result["status"] == "confirmation_required"

    @pytest.mark.asyncio
    async def test_confirmed_sends_request(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.post("/slots/s1/hold").mock(
            return_value=Response(200, json={"slot_id": "s1", "held_until": "2026-09-22T10:05:00Z"})
        )
        result = await hold_appointment_slot("s1", confirmed=True)
        assert result["slot_id"] == "s1"

    @pytest.mark.asyncio
    async def test_empty_slot_id(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await hold_appointment_slot("")
        assert "error" in result


class TestReleaseAppointmentSlot:
    @pytest.mark.asyncio
    async def test_mutations_disabled(self, mock_settings):
        mock_settings(chroniq_enable_mutations=False)
        result = await release_appointment_slot("s1")
        assert "Mutations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.post("/slots/s1/release").mock(
            return_value=Response(200, json={"success": True, "slot_id": "s1"})
        )
        result = await release_appointment_slot("s1")
        assert result["success"] is True

"""Tests for appointment tools — book, list, get, cancel."""

import pytest
from httpx import Response

from app.tools.appointments import (
    book_appointment,
    cancel_appointment,
    get_appointment_details,
    list_my_appointments,
)


class TestBookAppointment:
    @pytest.mark.asyncio
    async def test_mutations_disabled(self, mock_settings):
        mock_settings(chroniq_enable_mutations=False)
        result = await book_appointment("s1", "d1", confirmed=True)
        assert "Mutations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_confirmation(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await book_appointment("s1", "d1")
        assert result["status"] == "confirmation_required"
        assert result["action"] == "book_appointment"

    @pytest.mark.asyncio
    async def test_confirmed_sends_correct_body(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.post("/appointments").mock(
            return_value=Response(201, json={"id": "apt1", "status": "booked"})
        )
        result = await book_appointment(
            "s1", "d1", reason="Checkup", confirmed=True
        )
        assert result["status"] == "booked"
        import json
        body = json.loads(mock_api.calls[0].request.content)
        assert body["slot_id"] == "s1"
        assert body["doctor_id"] == "d1"
        assert body["reason"] == "Checkup"
        # Must NOT contain patient_name, patient_id, patient
        assert "patient_name" not in body
        assert "patient_id" not in body
        assert "patient" not in body

    @pytest.mark.asyncio
    async def test_missing_slot_id(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await book_appointment("", "d1", confirmed=True)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_missing_doctor_id(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await book_appointment("s1", "", confirmed=True)
        assert "error" in result


class TestListMyAppointments:
    @pytest.mark.asyncio
    async def test_uses_me_endpoint(self, mock_api, auth_token):
        mock_api.get("/appointments/me").mock(
            return_value=Response(200, json=[{"id": "apt1"}])
        )
        result = await list_my_appointments()
        assert result["count"] == 1
        # Verify it used /appointments/me, not /appointments
        assert mock_api.calls[0].request.url.path == "/appointments/me"


class TestGetAppointmentDetails:
    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token):
        mock_api.get("/appointments/apt1").mock(
            return_value=Response(200, json={"id": "apt1", "status": "booked"})
        )
        result = await get_appointment_details("apt1")
        assert result["id"] == "apt1"

    @pytest.mark.asyncio
    async def test_empty_id(self):
        result = await get_appointment_details("")
        assert "error" in result


class TestCancelAppointment:
    @pytest.mark.asyncio
    async def test_requires_confirmation(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await cancel_appointment("apt1")
        assert result["status"] == "confirmation_required"

    @pytest.mark.asyncio
    async def test_confirmed_uses_correct_route(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.post("/appointments/apt1/cancel").mock(
            return_value=Response(200, json={"id": "apt1", "status": "cancelled"})
        )
        result = await cancel_appointment("apt1", reason="Changed plans", confirmed=True)
        assert result["status"] == "cancelled"

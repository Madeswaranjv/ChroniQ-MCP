"""Tests for review tools."""

import pytest
from httpx import Response

from app.tools.reviews import (
    list_my_reviews,
    submit_appointment_review,
    update_appointment_review,
)


class TestListMyReviews:
    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token):
        mock_api.get("/reviews").mock(
            return_value=Response(200, json=[{"id": "r1", "doctor_rating": 5}])
        )
        result = await list_my_reviews()
        assert result["count"] == 1


class TestSubmitAppointmentReview:
    @pytest.mark.asyncio
    async def test_requires_confirmation(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await submit_appointment_review("apt1", 5, 4)
        assert result["status"] == "confirmation_required"

    @pytest.mark.asyncio
    async def test_invalid_doctor_rating(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await submit_appointment_review("apt1", 0, 4)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_hospital_rating(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await submit_appointment_review("apt1", 3, 6)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_wait_as_expected(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await submit_appointment_review("apt1", 4, 4, wait_as_expected="invalid")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_confirmed_sends_request(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.post("/reviews").mock(
            return_value=Response(201, json={"id": "r1", "appointment_id": "apt1"})
        )
        result = await submit_appointment_review(
            "apt1", 5, 4, comment="Great", confirmed=True
        )
        assert result["id"] == "r1"
        import json
        body = json.loads(mock_api.calls[0].request.content)
        assert body["doctor_rating"] == 5
        assert body["hospital_rating"] == 4


class TestUpdateAppointmentReview:
    @pytest.mark.asyncio
    async def test_mutations_disabled(self, mock_settings):
        mock_settings(chroniq_enable_mutations=False)
        result = await update_appointment_review("r1", doctor_rating=4)
        assert "Mutations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_rating(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await update_appointment_review("r1", doctor_rating=0)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.patch("/reviews/r1").mock(
            return_value=Response(200, json={"id": "r1", "success": True})
        )
        result = await update_appointment_review("r1", comment="Updated")
        assert result["success"] is True

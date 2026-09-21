"""Tests for discovery tools — public endpoints, no auth required."""

import pytest
import respx
from httpx import Response

from app.tools.discovery import (
    get_doctor_profile,
    get_hospital_details,
    list_hospitals,
    list_specialties,
    search_doctors,
)


class TestListHospitals:
    @pytest.mark.asyncio
    async def test_success(self, mock_api):
        mock_api.get("/hospitals").mock(
            return_value=Response(200, json=[{"id": "h1", "name": "City Hospital"}])
        )
        result = await list_hospitals()
        assert result["count"] == 1
        assert result["hospitals"][0]["name"] == "City Hospital"

    @pytest.mark.asyncio
    async def test_with_city_filter(self, mock_api):
        mock_api.get("/hospitals").mock(return_value=Response(200, json=[]))
        await list_hospitals(city="Chennai")
        req = mock_api.calls[0].request
        assert "city=Chennai" in str(req.url)

    @pytest.mark.asyncio
    async def test_invalid_rating(self):
        result = await list_hospitals(rating=6.0)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_lat_without_lng(self):
        result = await list_hospitals(lat=13.0)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_geo_search(self, mock_api):
        mock_api.get("/hospitals").mock(return_value=Response(200, json=[]))
        await list_hospitals(lat=13.0, lng=80.0, radius_km=10.0)
        req = mock_api.calls[0].request
        assert "lat=13" in str(req.url)
        assert "lng=80" in str(req.url)


class TestGetHospitalDetails:
    @pytest.mark.asyncio
    async def test_success(self, mock_api):
        mock_api.get("/hospitals/h1").mock(
            return_value=Response(200, json={"id": "h1", "name": "City Hospital", "departments": []})
        )
        result = await get_hospital_details("h1")
        assert result["id"] == "h1"

    @pytest.mark.asyncio
    async def test_empty_id(self):
        result = await get_hospital_details("")
        assert "error" in result


class TestSearchDoctors:
    @pytest.mark.asyncio
    async def test_success(self, mock_api):
        mock_api.get("/doctors").mock(
            return_value=Response(200, json=[{"id": "d1", "name": "Dr. Smith"}])
        )
        result = await search_doctors(specialty="Cardiology")
        assert result["count"] == 1
        req = mock_api.calls[0].request
        assert "specialty=Cardiology" in str(req.url)

    @pytest.mark.asyncio
    async def test_invalid_rating_min(self):
        result = await search_doctors(rating_min=6.0)
        assert "error" in result


class TestGetDoctorProfile:
    @pytest.mark.asyncio
    async def test_success(self, mock_api):
        mock_api.get("/doctors/d1").mock(
            return_value=Response(200, json={"id": "d1", "name": "Dr. Smith"})
        )
        result = await get_doctor_profile("d1")
        assert result["name"] == "Dr. Smith"

    @pytest.mark.asyncio
    async def test_empty_id(self):
        result = await get_doctor_profile("")
        assert "error" in result


class TestListSpecialties:
    @pytest.mark.asyncio
    async def test_success(self, mock_api):
        mock_api.get("/specialties").mock(
            return_value=Response(200, json=["Cardiology", "Dermatology"])
        )
        result = await list_specialties()
        assert result["count"] == 2
        assert "Cardiology" in result["specialties"]

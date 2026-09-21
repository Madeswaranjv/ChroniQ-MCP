"""Hospital, Doctor, and Specialty discovery tools (public — no auth required).

Backend routes:
  GET /hospitals           → list_hospitals
  GET /hospitals/{id}      → get_hospital_details
  GET /doctors             → search_doctors
  GET /doctors/{id}        → get_doctor_profile
  GET /specialties         → list_specialties
"""

from __future__ import annotations

from typing import Any

from app.clients.chroniq_api import api


async def list_hospitals(
    city: str | None = None,
    specialty: str | None = None,
    rating: float | None = None,
    search: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float | None = None,
) -> dict[str, Any]:
    """Search active hospitals with optional filters.

    Parameters
    ----------
    city : str, optional
        City name filter (case-insensitive exact match).
    specialty : str, optional
        Medical specialty — returns hospitals that have doctors of this specialty.
    rating : float, optional
        Minimum average rating (0.0–5.0).
    search : str, optional
        Free-text search on hospital name.
    lat : float, optional
        Latitude for geo search (must be paired with lng).
    lng : float, optional
        Longitude for geo search (must be paired with lat).
    radius_km : float, optional
        Search radius in kilometres (default 25, only used with lat/lng).
    """
    # Validate rating range
    if rating is not None and (rating < 0 or rating > 5):
        return {"error": "rating must be between 0.0 and 5.0"}

    # Validate coordinate pairing
    if (lat is not None) != (lng is not None):
        return {"error": "lat and lng must both be provided for geo search"}

    params: dict[str, Any] = {}
    if city:
        params["city"] = city
    if specialty:
        params["specialty"] = specialty
    if rating is not None:
        params["rating"] = rating
    if search:
        params["search"] = search
    if lat is not None:
        params["lat"] = lat
    if lng is not None:
        params["lng"] = lng
    if radius_km is not None:
        params["radius_km"] = radius_km

    data = await api.get("/hospitals", params=params)
    if isinstance(data, list):
        return {"hospitals": data, "count": len(data)}
    return data


async def get_hospital_details(id: str) -> dict[str, Any]:
    """Get full hospital details including departments and doctors.

    Parameters
    ----------
    id : str
        Hospital ID (custom_id or ObjectId).
    """
    if not id or not id.strip():
        return {"error": "Hospital ID is required."}
    return await api.get(f"/hospitals/{id}")


async def search_doctors(
    specialty: str | None = None,
    hospital_id: str | None = None,
    city: str | None = None,
    gender: str | None = None,
    language: str | None = None,
    fee_max: int | None = None,
    rating_min: float | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """Search for doctors across all hospitals with clinical and logistical filters.

    Parameters
    ----------
    specialty : str, optional
        Medical specialty filter.
    hospital_id : str, optional
        Restrict to a specific hospital.
    city : str, optional
        City filter.
    gender : str, optional
        Doctor gender filter.
    language : str, optional
        Language spoken by doctor.
    fee_max : int, optional
        Maximum consultation fee.
    rating_min : float, optional
        Minimum average rating (0.0–5.0).
    search : str, optional
        Free-text search on name or specialty.
    """
    if rating_min is not None and (rating_min < 0 or rating_min > 5):
        return {"error": "rating_min must be between 0.0 and 5.0"}

    params: dict[str, Any] = {}
    if specialty:
        params["specialty"] = specialty
    if hospital_id:
        params["hospital_id"] = hospital_id
    if city:
        params["city"] = city
    if gender:
        params["gender"] = gender
    if language:
        params["language"] = language
    if fee_max is not None:
        params["fee_max"] = fee_max
    if rating_min is not None:
        params["rating_min"] = rating_min
    if search:
        params["search"] = search

    data = await api.get("/doctors", params=params)
    if isinstance(data, list):
        return {"doctors": data, "count": len(data)}
    return data


async def get_doctor_profile(id: str) -> dict[str, Any]:
    """Get full public profile for a doctor.

    Parameters
    ----------
    id : str
        Doctor ID (custom_id or ObjectId).
    """
    if not id or not id.strip():
        return {"error": "Doctor ID is required."}
    return await api.get(f"/doctors/{id}")


async def list_specialties() -> dict[str, Any]:
    """List all distinct medical specialties offered by active doctors."""
    data = await api.get("/specialties")
    if isinstance(data, list):
        return {"specialties": data, "count": len(data)}
    return data

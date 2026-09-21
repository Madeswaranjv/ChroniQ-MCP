"""Patient profile tools — view and update.

Backend routes:
  GET   /patients/me/profile → get_patient_profile
  PATCH /users/me            → update_patient_profile
"""

from __future__ import annotations

from typing import Any

from app.clients.chroniq_api import api
from app.config import settings


async def get_patient_profile() -> dict[str, Any]:
    """Get the authenticated patient's profile information."""
    return await api.get("/patients/me/profile")


async def update_patient_profile(
    name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    preferred_language: str | None = None,
    photo_url: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Update profile attributes for the authenticated patient.

    ⚠ CONFIRMATION REQUIRED for sensitive changes (phone/email):
    Set confirmed=True to execute.

    The patient's role and ID cannot be modified. The backend validates
    uniqueness of phone and email.

    Parameters
    ----------
    name : str, optional
        Updated display name.
    phone : str, optional
        Updated phone number (must be unique).
    email : str, optional
        Updated email address (must be unique).
    age : int, optional
        Patient age.
    gender : str, optional
        Patient gender.
    preferred_language : str, optional
        Preferred language code (e.g. en, ta, hi, te, ml, kn).
    photo_url : str, optional
        URL to profile photo.
    confirmed : bool
        Must be True to execute this mutation.
    """
    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if phone is not None:
        body["phone"] = phone
    if email is not None:
        body["email"] = email
    if age is not None:
        body["age"] = age
    if gender is not None:
        body["gender"] = gender
    if preferred_language is not None:
        body["preferred_language"] = preferred_language
    if photo_url is not None:
        body["photo_url"] = photo_url

    if not body:
        return {"error": "At least one field must be provided to update."}

    # Require confirmation for sensitive contact info changes
    has_sensitive = phone is not None or email is not None
    if has_sensitive and not confirmed:
        return {
            "status": "confirmation_required",
            "action": "update_patient_profile",
            "changes": body,
            "message": "Changing contact information (phone/email). Call again with confirmed=True to proceed.",
        }

    return await api.patch("/users/me", json_body=body)

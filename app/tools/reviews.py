"""Review tools — list, submit, and update appointment reviews.

Backend routes:
  GET   /reviews      → list_my_reviews
  POST  /reviews      → submit_appointment_review
  PATCH /reviews/{id} → update_appointment_review

EXCLUDED:
  GET /reviews/by-appointment/{id} — authenticated but excluded per spec.

wait_as_expected valid values: shorter, as_expected, longer.
"""

from __future__ import annotations

from typing import Any

from app.clients.chroniq_api import api
from app.config import settings

_VALID_WAIT = frozenset({"shorter", "as_expected", "longer"})


async def list_my_reviews() -> dict[str, Any]:
    """List all reviews submitted by the authenticated patient."""
    data = await api.get("/reviews")
    if isinstance(data, list):
        return {"reviews": data, "count": len(data)}
    return data


async def submit_appointment_review(
    appointment_id: str,
    doctor_rating: int,
    hospital_rating: int,
    comment: str | None = None,
    tags: list[str] | None = None,
    wait_as_expected: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Submit a review for a completed appointment (one review per appointment).

    ⚠ CONFIRMATION REQUIRED: Set confirmed=True to execute.

    The backend enforces: appointment must exist, be owned by the caller,
    have status 'completed', and not already have a review. Duplicate
    reviews return 409 Conflict.

    Parameters
    ----------
    appointment_id : str
        Appointment ID (required).
    doctor_rating : int
        Doctor rating, 1–5 (required).
    hospital_rating : int
        Hospital rating, 1–5 (required).
    comment : str, optional
        Free-text comment.
    tags : list[str], optional
        Review tags.
    wait_as_expected : str, optional
        Wait experience: shorter, as_expected, or longer.
    confirmed : bool
        Must be True to execute this mutation.
    """
    if not appointment_id or not appointment_id.strip():
        return {"error": "appointment_id is required."}
    if not isinstance(doctor_rating, int) or doctor_rating < 1 or doctor_rating > 5:
        return {"error": "doctor_rating must be an integer between 1 and 5."}
    if not isinstance(hospital_rating, int) or hospital_rating < 1 or hospital_rating > 5:
        return {"error": "hospital_rating must be an integer between 1 and 5."}
    if wait_as_expected is not None and wait_as_expected not in _VALID_WAIT:
        return {"error": f"wait_as_expected must be one of: {', '.join(sorted(_VALID_WAIT))}"}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    if not confirmed:
        return {
            "status": "confirmation_required",
            "action": "submit_appointment_review",
            "appointment_id": appointment_id,
            "doctor_rating": doctor_rating,
            "hospital_rating": hospital_rating,
            "message": "This will submit a review for the appointment. Call again with confirmed=True to proceed.",
        }

    body: dict[str, Any] = {
        "appointment_id": appointment_id,
        "doctor_rating": doctor_rating,
        "hospital_rating": hospital_rating,
    }
    if comment is not None:
        body["comment"] = comment
    if tags is not None:
        body["tags"] = tags
    if wait_as_expected is not None:
        body["wait_as_expected"] = wait_as_expected

    return await api.post("/reviews", json_body=body)


async def update_appointment_review(
    id: str,
    doctor_rating: int | None = None,
    hospital_rating: int | None = None,
    comment: str | None = None,
    tags: list[str] | None = None,
    wait_as_expected: str | None = None,
) -> dict[str, Any]:
    """Edit an existing review within the 48-hour edit window.

    The backend enforces ownership and the 48-hour modification deadline.

    Parameters
    ----------
    id : str
        Review ID (required).
    doctor_rating : int, optional
        Updated doctor rating (1–5).
    hospital_rating : int, optional
        Updated hospital rating (1–5).
    comment : str, optional
        Updated comment.
    tags : list[str], optional
        Updated tags.
    wait_as_expected : str, optional
        Updated wait experience.
    """
    if not id or not id.strip():
        return {"error": "Review ID is required."}
    if doctor_rating is not None and (not isinstance(doctor_rating, int) or doctor_rating < 1 or doctor_rating > 5):
        return {"error": "doctor_rating must be an integer between 1 and 5."}
    if hospital_rating is not None and (not isinstance(hospital_rating, int) or hospital_rating < 1 or hospital_rating > 5):
        return {"error": "hospital_rating must be an integer between 1 and 5."}
    if wait_as_expected is not None and wait_as_expected not in _VALID_WAIT:
        return {"error": f"wait_as_expected must be one of: {', '.join(sorted(_VALID_WAIT))}"}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    body: dict[str, Any] = {}
    if doctor_rating is not None:
        body["doctor_rating"] = doctor_rating
    if hospital_rating is not None:
        body["hospital_rating"] = hospital_rating
    if comment is not None:
        body["comment"] = comment
    if tags is not None:
        body["tags"] = tags
    if wait_as_expected is not None:
        body["wait_as_expected"] = wait_as_expected

    if not body:
        return {"error": "At least one field must be provided to update."}

    return await api.patch(f"/reviews/{id}", json_body=body)

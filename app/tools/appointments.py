"""Appointment tools — book, list, view, and cancel.

Backend routes:
  POST  /appointments            → book_appointment
  GET   /appointments/me         → list_my_appointments
  GET   /appointments/{id}       → get_appointment_details
  POST  /appointments/{id}/cancel → cancel_appointment

BLOCKED:
  PATCH /appointments/{id}/reschedule → reschedule_appointment
    Reason: Non-atomic multi-save (Gap #6). Multiple sequential saves
    without a database transaction risk partial updates.
"""

from __future__ import annotations

from typing import Any

from app.clients.chroniq_api import api
from app.config import settings


async def book_appointment(
    slot_id: str,
    doctor_id: str,
    family_member_id: str | None = None,
    reason: str | None = None,
    symptoms_note: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Book an appointment using a previously held slot.

    ⚠ CONFIRMATION REQUIRED: Set confirmed=True to execute.

    The slot must be held first via hold_appointment_slot. Identity is
    derived from the authenticated JWT — patient_name, patient_id, and
    patient snapshot are never accepted as arguments.

    If family_member_id is provided, it should be a valid ID from the
    patient's own family member list (use list_family_members to verify).

    Parameters
    ----------
    slot_id : str
        ID of a previously held slot (required).
    doctor_id : str
        Doctor ID for the appointment (required).
    family_member_id : str, optional
        Book on behalf of a family member.
    reason : str, optional
        Reason for the visit.
    symptoms_note : str, optional
        Description of symptoms.
    confirmed : bool
        Must be True to execute this mutation.
    """
    if not slot_id or not slot_id.strip():
        return {"error": "slot_id is required."}
    if not doctor_id or not doctor_id.strip():
        return {"error": "doctor_id is required."}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    if not confirmed:
        return {
            "status": "confirmation_required",
            "action": "book_appointment",
            "slot_id": slot_id,
            "doctor_id": doctor_id,
            "family_member_id": family_member_id,
            "reason": reason,
            "message": "This will book an appointment. Call again with confirmed=True to proceed.",
        }

    body: dict[str, Any] = {
        "slot_id": slot_id,
        "doctor_id": doctor_id,
    }
    # Never send patient_name, patient, or patient_id
    if family_member_id:
        body["family_member_id"] = family_member_id
    if reason:
        body["reason"] = reason
    if symptoms_note:
        body["symptoms_note"] = symptoms_note

    return await api.post("/appointments", json_body=body)


async def list_my_appointments() -> dict[str, Any]:
    """List all appointments for the authenticated patient.

    Uses the patient-scoped /appointments/me endpoint (not the shared
    /appointments route which includes staff views).
    """
    data = await api.get("/appointments/me")
    if isinstance(data, list):
        return {"appointments": data, "count": len(data)}
    return data


async def get_appointment_details(id: str) -> dict[str, Any]:
    """Get details of a specific appointment.

    The backend enforces patient ownership — only your own appointments
    are accessible.

    Parameters
    ----------
    id : str
        Appointment ID or booking code.
    """
    if not id or not id.strip():
        return {"error": "Appointment ID or booking code is required."}
    return await api.get(f"/appointments/{id}")


async def cancel_appointment(
    id: str,
    reason: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Cancel a booked appointment.

    ⚠ CONFIRMATION REQUIRED: Set confirmed=True to execute.

    The backend enforces cancellation preconditions and patient ownership.

    Parameters
    ----------
    id : str
        Appointment ID (required).
    reason : str, optional
        Cancellation reason.
    confirmed : bool
        Must be True to execute this mutation.
    """
    if not id or not id.strip():
        return {"error": "Appointment ID is required."}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    if not confirmed:
        return {
            "status": "confirmation_required",
            "action": "cancel_appointment",
            "appointment_id": id,
            "message": "This will cancel the appointment. This action may be irreversible. Call again with confirmed=True to proceed.",
        }

    body: dict[str, Any] = {}
    if reason:
        body["reason"] = reason

    return await api.post(f"/appointments/{id}/cancel", json_body=body if body else None)

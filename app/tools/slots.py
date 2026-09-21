"""Slot discovery, hold, and release tools.

Backend routes:
  GET  /doctors/{id}/slots  → get_doctor_slots
  POST /slots/{id}/hold     → hold_appointment_slot
  POST /slots/{id}/release  → release_appointment_slot

⚠ get_doctor_slots has a documented database side effect: the backend calls
  generate_slots_for_doctor(id, days=14) which creates slot records if they
  do not already exist.  This is expected behaviour but is NOT strictly read-only.
"""

from __future__ import annotations

import re
from typing import Any

from app.clients.chroniq_api import api
from app.config import settings

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


async def get_doctor_slots(doctor_id: str, date: str) -> dict[str, Any]:
    """Retrieve bookable slots for a doctor on a given date.

    ⚠ SIDE EFFECT: The backend generates slot records for up to 14 days
    if they do not already exist. This is expected ChroniQ behaviour.

    Parameters
    ----------
    doctor_id : str
        Doctor ID.
    date : str
        Target date in YYYY-MM-DD format.
    """
    if not doctor_id or not doctor_id.strip():
        return {"error": "doctor_id is required."}
    if not _DATE_RE.match(date):
        return {"error": "date must be in YYYY-MM-DD format."}

    data = await api.get(f"/doctors/{doctor_id}/slots", params={"date": date})
    if isinstance(data, list):
        return {"slots": data, "count": len(data), "doctor_id": doctor_id, "date": date}
    return data


async def hold_appointment_slot(slot_id: str, confirmed: bool = False) -> dict[str, Any]:
    """Hold (lock) a slot for 5 minutes to prevent double-booking during checkout.

    Requires patient authentication. The backend enforces hold conditions
    and slot ownership.

    ⚠ CONFIRMATION REQUIRED: Set confirmed=True to execute.
    The hold lasts approximately 5 minutes. If the slot is already held or
    booked, a 409 Conflict will be returned.

    Parameters
    ----------
    slot_id : str
        Slot ID to hold.
    confirmed : bool
        Must be True to execute this mutation.
    """
    if not slot_id or not slot_id.strip():
        return {"error": "slot_id is required."}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    if not confirmed:
        return {
            "status": "confirmation_required",
            "action": "hold_appointment_slot",
            "slot_id": slot_id,
            "message": "This will hold the slot for ~5 minutes. Call again with confirmed=True to proceed.",
        }

    return await api.post(f"/slots/{slot_id}/hold")


async def release_appointment_slot(slot_id: str) -> dict[str, Any]:
    """Release a held slot back to available state.

    Requires patient authentication. The backend confirms the caller owns the hold.

    Parameters
    ----------
    slot_id : str
        Slot ID to release.
    """
    if not slot_id or not slot_id.strip():
        return {"error": "slot_id is required."}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    return await api.post(f"/slots/{slot_id}/release")

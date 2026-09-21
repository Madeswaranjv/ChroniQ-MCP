"""Support ticket tools — list and create.

Backend routes:
  GET  /support/tickets → list_support_tickets
  POST /support/tickets → create_support_ticket

Valid categories: booking_problem, queue_or_waiting, fee_or_payment,
                  app_problem, privacy_concern, other.
Valid contact_preference: in_app, email, sms.
"""

from __future__ import annotations

from typing import Any

from app.clients.chroniq_api import api
from app.config import settings

_VALID_CATEGORIES = frozenset({
    "booking_problem", "queue_or_waiting", "fee_or_payment",
    "app_problem", "privacy_concern", "other",
})

_VALID_CONTACT = frozenset({"in_app", "email", "sms"})


async def list_support_tickets() -> dict[str, Any]:
    """List all support tickets submitted by the authenticated patient."""
    data = await api.get("/support/tickets")
    if isinstance(data, list):
        return {"tickets": data, "count": len(data)}
    return data


async def create_support_ticket(
    category: str,
    description: str,
    appointment_id: str | None = None,
    hospital_id: str | None = None,
    contact_preference: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Create a new patient support ticket.

    ⚠ CONFIRMATION REQUIRED: Set confirmed=True to execute.

    Parameters
    ----------
    category : str
        Ticket category (required). One of: booking_problem, queue_or_waiting,
        fee_or_payment, app_problem, privacy_concern, other.
    description : str
        Detailed description of the issue (required).
    appointment_id : str, optional
        Related appointment ID, if applicable.
    hospital_id : str, optional
        Related hospital ID, if applicable.
    contact_preference : str, optional
        Preferred contact method: in_app, email, or sms (default: in_app).
    confirmed : bool
        Must be True to execute this mutation.
    """
    if not category or category not in _VALID_CATEGORIES:
        return {
            "error": f"Invalid category. Must be one of: {', '.join(sorted(_VALID_CATEGORIES))}",
        }
    if not description or not description.strip():
        return {"error": "description is required."}
    if contact_preference is not None and contact_preference not in _VALID_CONTACT:
        return {
            "error": f"Invalid contact_preference. Must be one of: {', '.join(sorted(_VALID_CONTACT))}",
        }

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    if not confirmed:
        return {
            "status": "confirmation_required",
            "action": "create_support_ticket",
            "category": category,
            "message": "This will create a support ticket. Call again with confirmed=True to proceed.",
        }

    body: dict[str, Any] = {
        "category": category,
        "description": description,
    }
    if appointment_id:
        body["appointment_id"] = appointment_id
    if hospital_id:
        body["hospital_id"] = hospital_id
    if contact_preference:
        body["contact_preference"] = contact_preference

    return await api.post("/support/tickets", json_body=body)

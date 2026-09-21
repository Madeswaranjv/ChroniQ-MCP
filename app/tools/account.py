"""Account-level tools — notification preferences.

Backend routes:
  PUT /users/me/notification-preferences → update_notification_preferences

BLOCKED tools (not registered):
  POST   /users/me/export         → export_patient_data
    Reason: Returns raw .dict() including file_path, password_hash.
  POST   /users/me/delete-request → request_account_deletion
    Reason: No purge worker exists (Gap #14).
  DELETE /users/me/delete-request → cancel_account_deletion
    Reason: Depends on request_account_deletion being enabled.
"""

from __future__ import annotations

from typing import Any

from app.clients.chroniq_api import api
from app.config import settings


async def update_notification_preferences(
    channels: dict[str, dict[str, bool]] | None = None,
    reminder_24h: bool | None = None,
    reminder_1h: bool | None = None,
) -> dict[str, Any]:
    """Update notification channel and timing preferences.

    Parameters
    ----------
    channels : dict, optional
        Nested dict mapping notification types to channel preferences.
        Each notification type key maps to a dict with boolean keys:
        in_app, email, sms.

        Notification type keys:
        booking_confirmed, reminder, doctor_delayed, queue_update,
        you_are_next, cancelled, rescheduled, system.

        Example::

            {
                "booking_confirmed": {"in_app": true, "email": true, "sms": true},
                "reminder": {"in_app": true, "email": true, "sms": false}
            }

    reminder_24h : bool, optional
        Enable 24-hour appointment reminder.
    reminder_1h : bool, optional
        Enable 1-hour appointment reminder.
    """
    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    body: dict[str, Any] = {}
    if channels is not None:
        body["channels"] = channels
    if reminder_24h is not None:
        body["reminder_24h"] = reminder_24h
    if reminder_1h is not None:
        body["reminder_1h"] = reminder_1h

    if not body:
        return {"error": "At least one preference field must be provided."}

    return await api.put("/users/me/notification-preferences", json_body=body)

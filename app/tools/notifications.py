"""Notification tools — list and mark as read.

Backend routes:
  GET   /notifications          → list_notifications
  PATCH /notifications/{id}/read → mark_notification_as_read

⚠ KNOWN ISSUE: The Notification model stores content in the ``body`` field,
but the notifications route returns it as ``message``.  Because the model
has no ``message`` attribute, the value may be null.  This tool returns
whichever field is present and non-null, preferring ``message`` if available,
falling back to ``body``.
"""

from __future__ import annotations

from typing import Any

from app.clients.chroniq_api import api
from app.config import settings


async def list_notifications() -> dict[str, Any]:
    """List notifications for the authenticated patient (most recent first, max 50).

    ⚠ Due to a backend field mismatch (model stores 'body' but route
    returns 'message'), the notification text may appear in either field.
    Both are included when available.
    """
    data = await api.get("/notifications")
    if isinstance(data, list):
        # Normalise the body/message mismatch
        normalised = []
        for n in data:
            if isinstance(n, dict):
                # Ensure both keys are available to the consumer
                msg = n.get("message") or n.get("body")
                n["message"] = msg
                n["body"] = msg
            normalised.append(n)
        return {"notifications": normalised, "count": len(normalised)}
    return data


async def mark_notification_as_read(id: str) -> dict[str, Any]:
    """Mark a notification as read.

    The backend enforces ownership — only your own notifications
    can be marked.

    Parameters
    ----------
    id : str
        Notification ID (required).
    """
    if not id or not id.strip():
        return {"error": "Notification ID is required."}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    return await api.patch(f"/notifications/{id}/read")

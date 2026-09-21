"""Medical document tools — list and update metadata.

Backend routes:
  GET   /documents      → list_medical_documents
  PATCH /documents/{id} → update_medical_document

BLOCKED:
  DELETE /documents/{id} → delete_medical_document
    Reason: Physical file not deleted from storage (Gap #13).
  POST /documents → upload (multipart, excluded by design)

Valid categories: lab_report, prescription, imaging, discharge_summary, other.
"""

from __future__ import annotations

from typing import Any

from app.clients.chroniq_api import api
from app.config import settings

_VALID_CATEGORIES = frozenset({
    "lab_report", "prescription", "imaging", "discharge_summary", "other",
})


async def list_medical_documents() -> dict[str, Any]:
    """List uploaded medical documents for the authenticated patient.

    Returns metadata only — file paths are never revealed.
    """
    data = await api.get("/documents")
    if isinstance(data, list):
        return {"documents": data, "count": len(data)}
    return data


async def update_medical_document(
    id: str,
    name: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """Update a medical document's label or category.

    The backend enforces ownership — only your own documents can be modified.

    Parameters
    ----------
    id : str
        Document ID (required).
    name : str, optional
        Updated document name/label.
    category : str, optional
        Updated category. Must be one of: lab_report, prescription,
        imaging, discharge_summary, other.
    """
    if not id or not id.strip():
        return {"error": "Document ID is required."}

    if category is not None and category not in _VALID_CATEGORIES:
        return {
            "error": f"Invalid category '{category}'. Must be one of: {', '.join(sorted(_VALID_CATEGORIES))}",
        }

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if category is not None:
        body["category"] = category

    if not body:
        return {"error": "At least one field (name or category) must be provided to update."}

    return await api.patch(f"/documents/{id}", json_body=body)

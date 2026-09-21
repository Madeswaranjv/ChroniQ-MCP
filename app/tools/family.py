"""Family member management tools.

Backend routes:
  GET    /patients/me/family   → list_family_members
  POST   /family-members       → add_family_member
  PATCH  /family-members/{id}  → update_family_member
  DELETE /family-members/{id}  → delete_family_member

Backend policy: maximum 6 family members per patient.
"""

from __future__ import annotations

from typing import Any

from app.clients.chroniq_api import api
from app.config import settings


async def list_family_members() -> dict[str, Any]:
    """List all family members registered under the authenticated patient."""
    data = await api.get("/patients/me/family")
    if isinstance(data, list):
        return {"family_members": data, "count": len(data)}
    return data


async def add_family_member(
    name: str,
    relation: str,
    age: int | None = None,
    gender: str | None = None,
) -> dict[str, Any]:
    """Add a dependent family member.

    The backend enforces a maximum of 6 family members per patient.

    Parameters
    ----------
    name : str
        Family member's name (required).
    relation : str
        Relationship (e.g. spouse, son, daughter, father, mother, brother,
        sister, grandparent, other) (required).
    age : int, optional
        Family member's age.
    gender : str, optional
        Family member's gender.
    """
    if not name or not name.strip():
        return {"error": "name is required."}
    if not relation or not relation.strip():
        return {"error": "relation is required."}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    body: dict[str, Any] = {"name": name, "relation": relation}
    if age is not None:
        body["age"] = age
    if gender is not None:
        body["gender"] = gender

    return await api.post("/family-members", json_body=body)


async def update_family_member(
    id: str,
    name: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    relation: str | None = None,
) -> dict[str, Any]:
    """Update an existing family member's details.

    The backend enforces ownership — only your own family members
    can be modified.

    Parameters
    ----------
    id : str
        Family member ID (required).
    name : str, optional
        Updated name.
    age : int, optional
        Updated age.
    gender : str, optional
        Updated gender.
    relation : str, optional
        Updated relationship.
    """
    if not id or not id.strip():
        return {"error": "Family member ID is required."}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if age is not None:
        body["age"] = age
    if gender is not None:
        body["gender"] = gender
    if relation is not None:
        body["relation"] = relation

    if not body:
        return {"error": "At least one field must be provided to update."}

    return await api.patch(f"/family-members/{id}", json_body=body)


async def delete_family_member(
    id: str,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Delete a family member.

    ⚠ CONFIRMATION REQUIRED: Set confirmed=True to execute.

    The backend enforces ownership — only your own family members
    can be deleted.

    Parameters
    ----------
    id : str
        Family member ID (required).
    confirmed : bool
        Must be True to execute this deletion.
    """
    if not id or not id.strip():
        return {"error": "Family member ID is required."}

    if not settings.chroniq_enable_mutations:
        return {"error": "Mutations are disabled. Set CHRONIQ_ENABLE_MUTATIONS=true to enable write operations."}

    if not confirmed:
        return {
            "status": "confirmation_required",
            "action": "delete_family_member",
            "family_member_id": id,
            "message": "This will permanently delete the family member. Call again with confirmed=True to proceed.",
        }

    return await api.delete(f"/family-members/{id}")

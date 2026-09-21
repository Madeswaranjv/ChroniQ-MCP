"""Tests for family member tools."""

import pytest
from httpx import Response

from app.tools.family import (
    add_family_member,
    delete_family_member,
    list_family_members,
    update_family_member,
)


class TestListFamilyMembers:
    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token):
        mock_api.get("/patients/me/family").mock(
            return_value=Response(200, json=[{"id": "fm1", "name": "Spouse"}])
        )
        result = await list_family_members()
        assert result["count"] == 1


class TestAddFamilyMember:
    @pytest.mark.asyncio
    async def test_mutations_disabled(self, mock_settings):
        mock_settings(chroniq_enable_mutations=False)
        result = await add_family_member("Test", "spouse")
        assert "Mutations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.post("/family-members").mock(
            return_value=Response(201, json={"id": "fm1", "name": "Child", "relation": "son"})
        )
        result = await add_family_member("Child", "son", age=5)
        assert result["name"] == "Child"

    @pytest.mark.asyncio
    async def test_missing_name(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await add_family_member("", "spouse")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_missing_relation(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await add_family_member("Test", "")
        assert "error" in result


class TestUpdateFamilyMember:
    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.patch("/family-members/fm1").mock(
            return_value=Response(200, json={"id": "fm1", "name": "Updated"})
        )
        result = await update_family_member("fm1", name="Updated")
        assert result["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_no_fields(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await update_family_member("fm1")
        assert "error" in result


class TestDeleteFamilyMember:
    @pytest.mark.asyncio
    async def test_requires_confirmation(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await delete_family_member("fm1")
        assert result["status"] == "confirmation_required"

    @pytest.mark.asyncio
    async def test_confirmed(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.delete("/family-members/fm1").mock(
            return_value=Response(200, json={"success": True})
        )
        result = await delete_family_member("fm1", confirmed=True)
        assert result["success"] is True

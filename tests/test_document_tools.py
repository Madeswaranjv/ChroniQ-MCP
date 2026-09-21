"""Tests for medical document tools."""

import pytest
from httpx import Response

from app.tools.documents import list_medical_documents, update_medical_document


class TestListMedicalDocuments:
    @pytest.mark.asyncio
    async def test_success(self, mock_api, auth_token):
        mock_api.get("/documents").mock(
            return_value=Response(200, json=[{"id": "doc1", "name": "Lab Report"}])
        )
        result = await list_medical_documents()
        assert result["count"] == 1
        # Verify file_path is not in response (sanitised by client)
        assert "file_path" not in str(result)


class TestUpdateMedicalDocument:
    @pytest.mark.asyncio
    async def test_mutations_disabled(self, mock_settings):
        mock_settings(chroniq_enable_mutations=False)
        result = await update_medical_document("doc1", name="Renamed")
        assert "Mutations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_category(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await update_medical_document("doc1", category="invalid")
        assert "error" in result
        assert "Invalid category" in result["error"]

    @pytest.mark.asyncio
    async def test_valid_category(self, mock_api, auth_token, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        mock_api.patch("/documents/doc1").mock(
            return_value=Response(200, json={"id": "doc1", "category": "lab_report"})
        )
        result = await update_medical_document("doc1", category="lab_report")
        assert result["category"] == "lab_report"

    @pytest.mark.asyncio
    async def test_no_fields(self, mock_settings):
        mock_settings(chroniq_enable_mutations=True)
        result = await update_medical_document("doc1")
        assert "error" in result

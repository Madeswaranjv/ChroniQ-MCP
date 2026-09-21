"""Tests for app.clients.chroniq_api — HTTP client behaviour."""

import pytest
import respx
from httpx import Response

from app.auth import set_caller_bearer_token
from app.clients.chroniq_api import ChroniqAPI, ChroniqAPIError, _sanitise


class TestSanitise:
    def test_strips_password_hash(self):
        assert _sanitise({"name": "Alice", "password_hash": "xxx"}) == {"name": "Alice"}

    def test_strips_file_path(self):
        assert _sanitise({"id": "1", "file_path": "/data/x.pdf"}) == {"id": "1"}

    def test_strips_nested(self):
        data = {"user": {"name": "Bob", "password_hash": "h", "google_id": "g"}}
        assert _sanitise(data) == {"user": {"name": "Bob"}}

    def test_strips_in_list(self):
        data = [{"id": "1", "file_path": "/x"}, {"id": "2"}]
        assert _sanitise(data) == [{"id": "1"}, {"id": "2"}]

    def test_preserves_non_sensitive(self):
        data = {"id": "1", "name": "Test", "status": "active"}
        assert _sanitise(data) == data


class TestChroniqAPIBearerForwarding:
    @pytest.mark.asyncio
    async def test_bearer_token_sent(self, mock_api):
        set_caller_bearer_token("patient-jwt-abc")
        mock_api.get("/hospitals").mock(return_value=Response(200, json=[]))

        client = ChroniqAPI()
        await client.get("/hospitals")

        req = mock_api.calls[0].request
        assert req.headers["authorization"] == "Bearer patient-jwt-abc"

    @pytest.mark.asyncio
    async def test_no_token_no_header(self, mock_api):
        set_caller_bearer_token(None)
        mock_api.get("/hospitals").mock(return_value=Response(200, json=[]))

        client = ChroniqAPI(base_url="http://127.0.0.1:8000")
        await client.get("/hospitals")

        req = mock_api.calls[0].request
        assert "authorization" not in req.headers


class TestChroniqAPIErrors:
    @pytest.mark.asyncio
    async def test_401_raises(self, mock_api):
        mock_api.get("/patients/me/profile").mock(
            return_value=Response(401, json={"detail": "Token expired"})
        )
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="session may have expired"):
            await client.get("/patients/me/profile")

    @pytest.mark.asyncio
    async def test_403_raises(self, mock_api):
        mock_api.get("/appointments/xyz").mock(
            return_value=Response(403, json={"detail": "Access forbidden"})
        )
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="permission"):
            await client.get("/appointments/xyz")

    @pytest.mark.asyncio
    async def test_404_raises(self, mock_api):
        mock_api.get("/hospitals/nonexistent").mock(
            return_value=Response(404, json={"detail": "Hospital not found"})
        )
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="not found"):
            await client.get("/hospitals/nonexistent")

    @pytest.mark.asyncio
    async def test_409_raises(self, mock_api):
        mock_api.post("/slots/s1/hold").mock(
            return_value=Response(409, json={"detail": "Slot already held"})
        )
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="Conflict"):
            await client.post("/slots/s1/hold")

    @pytest.mark.asyncio
    async def test_429_raises(self, mock_api):
        mock_api.get("/hospitals").mock(return_value=Response(429, json={}))
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="Rate limit"):
            await client.get("/hospitals")

    @pytest.mark.asyncio
    async def test_500_raises(self, mock_api):
        mock_api.get("/hospitals").mock(return_value=Response(500, json={}))
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="internal error"):
            await client.get("/hospitals")

    @pytest.mark.asyncio
    async def test_503_raises(self, mock_api):
        mock_api.get("/hospitals").mock(return_value=Response(503, json={}))
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="unavailable"):
            await client.get("/hospitals")

    @pytest.mark.asyncio
    async def test_malformed_json(self, mock_api):
        mock_api.get("/hospitals").mock(
            return_value=Response(200, content=b"not json", headers={"content-type": "text/plain"})
        )
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="invalid response"):
            await client.get("/hospitals")

    @pytest.mark.asyncio
    async def test_timeout(self, mock_api):
        import httpx
        mock_api.get("/hospitals").mock(side_effect=httpx.ReadTimeout("timeout"))
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="did not respond"):
            await client.get("/hospitals")

    @pytest.mark.asyncio
    async def test_connection_error(self, mock_api):
        import httpx
        mock_api.get("/hospitals").mock(side_effect=httpx.ConnectError("refused"))
        client = ChroniqAPI()
        with pytest.raises(ChroniqAPIError, match="Could not connect"):
            await client.get("/hospitals")


class TestChroniqAPISuccess:
    @pytest.mark.asyncio
    async def test_get_returns_sanitised_json(self, mock_api):
        mock_api.get("/hospitals").mock(
            return_value=Response(200, json=[
                {"id": "h1", "name": "City Hospital", "password_hash": "secret"}
            ])
        )
        client = ChroniqAPI()
        result = await client.get("/hospitals")
        assert result == [{"id": "h1", "name": "City Hospital"}]

    @pytest.mark.asyncio
    async def test_post_sends_json_body(self, mock_api):
        mock_api.post("/appointments").mock(
            return_value=Response(201, json={"id": "apt1", "status": "booked"})
        )
        client = ChroniqAPI()
        result = await client.post("/appointments", json_body={"slot_id": "s1", "doctor_id": "d1"})
        assert result["status"] == "booked"

        req = mock_api.calls[0].request
        import json
        body = json.loads(req.content)
        assert body["slot_id"] == "s1"

    @pytest.mark.asyncio
    async def test_query_params_none_filtered(self, mock_api):
        mock_api.get("/doctors").mock(return_value=Response(200, json=[]))
        client = ChroniqAPI()
        await client.get("/doctors", params={"specialty": "Cardiology", "city": None})

        req = mock_api.calls[0].request
        assert "city" not in str(req.url)
        assert "specialty=Cardiology" in str(req.url)

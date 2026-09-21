"""Shared asynchronous HTTP client for the ChroniQ backend.

Security invariants
-------------------
* ``path`` is always a fixed string defined in trusted tool code.
* The model/user can NEVER supply an arbitrary URL, HTTP method, or path.
* Access tokens are forwarded but never logged.
* Raw stack traces and sensitive response bodies are never surfaced.
* Non-idempotent writes are never automatically retried.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.auth import get_caller_bearer_token
from app.config import settings

logger = logging.getLogger("chroniq_mcp.api_client")

# Fields that must never be returned to the model context
_SENSITIVE_FIELDS = frozenset({
    "password_hash",
    "file_path",
    "code_hash",
    "google_id",
    "otp",
    "refresh_token",
    "_id",
    "__v",
})


class ChroniqAPIError(RuntimeError):
    """Raised when a ChroniQ backend request fails in a structured way."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _sanitise(obj: Any) -> Any:
    """Recursively strip sensitive keys from response data."""
    if isinstance(obj, dict):
        return {
            k: _sanitise(v)
            for k, v in obj.items()
            if k not in _SENSITIVE_FIELDS
        }
    if isinstance(obj, list):
        return [_sanitise(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Friendly messages by HTTP status
# ---------------------------------------------------------------------------
_STATUS_MESSAGES: dict[int, str] = {
    400: "Bad request — check the supplied arguments.",
    401: "Authentication failed — your session may have expired. Please log in again.",
    403: "Access denied — you do not have permission for this operation.",
    404: "The requested resource was not found.",
    409: "Conflict — this operation cannot be completed (e.g. duplicate or state mismatch).",
    429: "Rate limit exceeded — please wait a moment before trying again.",
    500: "The ChroniQ server encountered an internal error. Please try again later.",
    503: "The ChroniQ service is temporarily unavailable. Please try again later.",
}


class ChroniqAPI:
    """Async HTTP adapter for the ChroniQ REST backend."""

    def __init__(
        self,
        base_url: str | None = None,
        connect_timeout: float | None = None,
        request_timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.chroniq_api_base_url).rstrip("/")
        self.timeout = httpx.Timeout(
            connect=connect_timeout or settings.chroniq_connect_timeout,
            read=request_timeout or settings.chroniq_request_timeout,
            write=request_timeout or settings.chroniq_request_timeout,
            pool=request_timeout or settings.chroniq_request_timeout,
        )

    # ----- internal helpers --------------------------------------------------

    def _build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build request headers with bearer-token injection."""
        headers: dict[str, str] = {"Accept": "application/json"}
        token = get_caller_bearer_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if extra:
            headers.update(extra)
        return headers

    # ----- public request methods -------------------------------------------

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Execute a request against a **fixed** ChroniQ backend path.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, PATCH, PUT, DELETE).
        path : str
            Backend route — must be a constant from tool code.
        params : dict, optional
            Query-string parameters.
        json_body : dict, optional
            JSON request body.
        headers : dict, optional
            Extra headers (merged with auth header).

        Returns
        -------
        dict | list
            Sanitised JSON response.

        Raises
        ------
        ChroniqAPIError
            On any HTTP or connectivity failure.
        """
        merged_headers = self._build_headers(headers)

        # Remove None-valued query params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=False,
            ) as client:
                response = await client.request(
                    method,
                    path,
                    params=params,
                    json=json_body,
                    headers=merged_headers,
                )
        except httpx.TimeoutException:
            logger.warning("Request to %s %s timed out", method, path)
            raise ChroniqAPIError(
                "The ChroniQ backend did not respond in time. Please try again.",
            )
        except httpx.ConnectError:
            logger.warning("Connection refused for %s %s", method, path)
            raise ChroniqAPIError(
                "Could not connect to the ChroniQ backend. "
                "Ensure the backend is running and reachable.",
            )
        except httpx.HTTPError as exc:
            logger.warning("HTTP error for %s %s: %s", method, path, type(exc).__name__)
            raise ChroniqAPIError(
                "An unexpected network error occurred while contacting ChroniQ.",
            )

        # Handle error status codes
        if response.is_error:
            status_code = response.status_code
            friendly = _STATUS_MESSAGES.get(
                status_code,
                f"ChroniQ returned an unexpected HTTP {status_code} error.",
            )
            # Try to extract backend detail (if safe)
            detail = ""
            try:
                body = response.json()
                if isinstance(body, dict) and "detail" in body:
                    raw_detail = body["detail"]
                    # Only surface non-sensitive string details
                    if isinstance(raw_detail, str) and len(raw_detail) < 300:
                        detail = raw_detail
            except Exception:
                pass

            msg = f"{friendly} {detail}".strip() if detail else friendly
            logger.info(
                "ChroniQ %s %s → HTTP %d", method, path, status_code,
            )
            raise ChroniqAPIError(msg, status_code=status_code)

        # Parse JSON
        try:
            data = response.json()
        except ValueError:
            raise ChroniqAPIError(
                "The ChroniQ backend returned an invalid response.",
            )

        return _sanitise(data)

    # ----- convenience wrappers ---------------------------------------------

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> Any:
        return await self.request("PATCH", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> Any:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Any:
        return await self.request("DELETE", path, **kwargs)


# Module-level singleton
api = ChroniqAPI()

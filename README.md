# ChroniQ MCP Server

A standalone **Model Context Protocol (MCP) server** that exposes verified patient-facing ChroniQ healthcare features to the **Healix** AI assistant.

## Architecture

```
┌─────────────┐   Streamable HTTP (/mcp)   ┌───────────────┐        HTTP REST        ┌──────────────┐
│   Healix    │ ◄────────────────────────► │  chroniq-mcp  │ ◄──────────────────────► │  ChroniQ     │
│ (AI Client) │       or stdio / sse       │  MCP Server   │                          │  Backend     │
└─────────────┘                            └───────────────┘                          └──────┬───────┘
                                                                                             │
                                                                                       MongoDB Atlas
```

- **Separate project**: Runs completely independently of the ChroniQ backend and frontend.
- **HTTP REST only**: Communicates with ChroniQ exclusively through HTTP requests.
- **No direct database access**: Never connects to MongoDB Atlas directly; all authorization and business rules are enforced by the ChroniQ backend.
- **Patient-facing only**: Exposes only verified patient workflows. No staff, doctor, clinic admin, kiosk, or auth credentials endpoints are exposed.

---

## Supported Transports & Endpoints

| Transport | Endpoint / Mode | Purpose |
|---|---|---|
| **Streamable HTTP** *(Default)* | `http://0.0.0.0:8001/mcp` | Recommended modern MCP transport for Healix, Render deployment, and remote clients. Supports per-request `Authorization: Bearer <jwt>` headers via Starlette middleware. |
| **SSE** | `http://0.0.0.0:8001/sse` | Legacy Server-Sent Events MCP transport. |
| **stdio** | Standard I/O streams | Local CLI desktop clients (e.g. Claude Desktop, Cursor). |

---

## Prerequisites

- Python 3.11+
- ChroniQ backend running and reachable (default: `http://127.0.0.1:8000`)
- Valid patient JWT access token (HS256) for protected operations

---

## Installation (No Virtual Environment)

Per project requirements, install dependencies directly using pip without virtual environments:

```bash
cd e:\KLN\ChroniQ-MCP
python -m pip install -e ".[dev]"
```

---

## Configuration & Environment Variables

Copy `.env.example` to `.env` or set environment variables:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `CHRONIQ_API_BASE_URL` | `http://127.0.0.1:8000` | ChroniQ FastAPI backend base URL (must start with `http://` or `https://`) |
| `CHRONIQ_REQUEST_TIMEOUT` | `15.0` | HTTP request/read/write timeout in seconds (must be > 0) |
| `CHRONIQ_CONNECT_TIMEOUT` | `5.0` | HTTP connection timeout in seconds (must be > 0) |
| `MCP_HOST` | `0.0.0.0` | Bind host for HTTP transports (`0.0.0.0` allows external/container access) |
| `MCP_PORT` | `8001` | Bind port for MCP server (1–65535). Automatically aliases hosting `PORT` |
| `PORT` | *(None)* | Hosting platform port (e.g. Render). Automatically mapped to `MCP_PORT` |
| `MCP_TRANSPORT` | `streamable-http` | Protocol transport: `streamable-http`, `sse`, or `stdio` |
| `MCP_PATH` | `/mcp` | HTTP path for Streamable HTTP endpoint |
| `CHRONIQ_ENABLE_MUTATIONS` | `false` | Master safety gate. Write operations rejected when `false` |
| `CHRONIQ_AUTH_TOKEN` | *(empty)* | Dev-only single-patient bearer token fallback for local/stdio testing |

> [!WARNING]
> Never put real secrets, admin tokens, or production JWTs in `.env`. `CHRONIQ_AUTH_TOKEN` is strictly a fallback for single-user local development. In production/HTTP mode, tokens must be supplied in incoming request headers.

---

## Starting the MCP Server

### Default (Streamable HTTP on `0.0.0.0:8001/mcp`):
```bash
python -m app.server
```
or with Uvicorn directly:
```bash
uvicorn app.server:app --host 0.0.0.0 --port 8001
```

### With Custom Arguments:
```bash
python -m app.server --host 127.0.0.1 --port 8005 --path /mcp
```

### Stdio Mode (for desktop clients):
```bash
python -m app.server --transport stdio
```

---

## Connecting an MCP Client

### 1. Connecting via Streamable HTTP (Healix / Remote MCP Client)
Configure the client with endpoint URL:
```
http://<host>:<port>/mcp
```
For authenticated requests, the client includes the standard HTTP header:
```http
Authorization: Bearer <patient-jwt-token>
```
The server's `BearerAuthMiddleware` extracts the token into an isolated `ContextVar` for each request task, ensuring patient tokens never cross-contaminate concurrent requests.

### 2. Desktop MCP Client Configuration (e.g. Claude Desktop - Stdio)
Add to your client configuration file (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "chroniq": {
      "command": "python",
      "args": ["-m", "app.server", "--transport", "stdio"],
      "cwd": "e:\\KLN\\ChroniQ-MCP",
      "env": {
        "CHRONIQ_API_BASE_URL": "http://127.0.0.1:8000",
        "CHRONIQ_AUTH_TOKEN": "<your-dev-patient-jwt>",
        "CHRONIQ_ENABLE_MUTATIONS": "false"
      }
    }
  }
}
```

### 3. Running the Local Smoke Test Client
Verify MCP connection, handshake, discovery, and tool calling:
```bash
python smoke_test.py
```

---

## Running Automated Tests

Run the full test suite (129 tests):
```bash
python -m pytest tests/ -v
```

All unit and transport tests use mocked backend routes using `respx` — zero external network or database dependencies are required to run tests.

---

## Authentication & Patient Isolation Design

1. **Per-Request Isolation**: Under HTTP/StreamableHTTP, incoming `Authorization: Bearer <jwt>` headers are parsed by `BearerAuthMiddleware` and placed in Python's async `ContextVar`. Each request task has complete isolation — tokens cannot leak between concurrent patient sessions.
2. **Identity from Token Only**: The server derives identity strictly from the verified JWT on the backend. No tool accepts `patient_id`, `user_id`, or `role` parameters.
3. **No Secret Leaks**: Bearer tokens, passwords, OTPs, and private hashes are filtered out of error messages, exceptions, logs, and response structures.
4. **Dev Fallback**: If no per-request HTTP header is provided, `get_caller_bearer_token()` falls back to `CHRONIQ_AUTH_TOKEN` (convenient for local CLI / stdio development). In production, keep `CHRONIQ_AUTH_TOKEN` unset.

---

## Tool Inventory: 28 Enabled Tools

| Category | Tools | Auth Required | Mutating |
|---|---|---|---|
| **Discovery** | `list_hospitals`, `get_hospital_details`, `search_doctors`, `get_doctor_profile`, `list_specialties` | No | No |
| **Slots** | `get_doctor_slots`, `hold_appointment_slot`, `release_appointment_slot` | Mixed | Yes (`hold`, `release`) |
| **Appointments** | `list_my_appointments`, `get_appointment_details`, `book_appointment`, `cancel_appointment` | Yes | Yes (`book`, `cancel`) |
| **Patient Profile** | `get_patient_profile`, `update_patient_profile` | Yes | Yes (`update`) |
| **Family Members** | `list_family_members`, `add_family_member`, `update_family_member`, `delete_family_member` | Yes | Yes (`add`, `update`, `delete`) |
| **Medical Documents** | `list_medical_documents`, `update_medical_document` | Yes | Yes (`update`) |
| **Reviews** | `list_my_reviews`, `submit_appointment_review`, `update_appointment_review` | Yes | Yes (`submit`, `update`) |
| **Support** | `list_support_tickets`, `create_support_ticket` | Yes | Yes (`create`) |
| **Notifications** | `list_notifications`, `mark_notification_as_read` | Yes | Yes (`mark_read`) |
| **Account Preferences** | `update_notification_preferences` | Yes | Yes (`update`) |

---

## 8 Blocked Tools & Why They Remain Blocked

The following 8 endpoints are **intentionally NOT registered** in the MCP server due to critical security and integrity vulnerabilities identified in the ChroniQ backend:

1. `reschedule_appointment` (Gap #6): Non-atomic multi-save without transaction. A failure halfway through leaves the patient with either two appointments or none.
2. `check_in_appointment` (Gap #1): Uses `get_optional_user` with no mandatory authentication enforcement. Anyone can check in an appointment if they know the ID.
3. `get_patient_queue_status` (Gap #2): No authentication required and no patient ownership check. Allows enumerating queue status for any patient.
4. `get_department_queue_board` (Gap #9): Unauthenticated endpoint that publicly exposes internal appointment IDs on department boards.
5. `delete_medical_document` (Gap #13): Deletes MongoDB record but fails to delete physical files from the storage disk.
6. `request_account_deletion` (Gap #14): Sets deletion status flag but no backend purge worker exists; data remains indefinitely.
7. `cancel_account_deletion`: Blocked because account deletion workflow is incomplete and untested.
8. `export_patient_data`: Exports raw patient records without field masking or sanitization, potentially leaking internal security hashes.

---

## Mutation Safety & Confirmation Gates

1. **Master Gate (`CHRONIQ_ENABLE_MUTATIONS=false`)**:
   All write/mutating operations (`POST`, `PATCH`, `PUT`, `DELETE`) are rejected *before* any request is sent to the backend.
2. **Explicit Confirmation (`confirmed=True`)**:
   Even with mutations enabled, high-impact operations require deliberate user confirmation (`confirmed=True` parameter):
   - Booking an appointment (`book_appointment`)
   - Holding a slot (`hold_appointment_slot`)
   - Cancelling an appointment (`cancel_appointment`)
   - Deleting a family member (`delete_family_member`)
   - Submitting a review (`submit_appointment_review`)
   - Creating a support ticket (`create_support_ticket`)
   - Modifying sensitive profile fields (email, phone) via `update_patient_profile`

If `confirmed=False`, the tool aborts with an instruction detailing the required confirmation.

---

## What Is Verified vs Not Tested

### Verified
- **129 Automated Tests Passed**: All configuration validation, tool input schemas, mutation gates, confirmation guards, error sanitization, and security boundaries.
- **Streamable HTTP Transport & Protocol Handshake**: Fully verified with live MCP `ClientSession` over HTTP endpoint `/mcp`.
- **Tool Discovery**: Verified that exactly 28 tools are returned through the protocol and 8 blocked tools are absent.
- **Authentication & Isolation**: Verified that Bearer tokens are correctly extracted from HTTP headers and forwarded to backend requests, with complete isolation across concurrent requests.
- **FastAPI Backend Liveness**: Confirmed ChroniQ FastAPI REST backend is running live on `http://127.0.0.1:8000` with `/health` returning HTTP 200 `{"status": "healthy"}`.

### Verified with Mocks Only
- Data responses from ChroniQ backend endpoints (`/specialties`, `/hospitals`, `/doctors`, `/appointments/me`, etc.) were tested with mocks because the live local backend's MongoDB Atlas connection rejected queries due to Atlas IP whitelist restrictions.

### Blocking Issues for Live End-to-End Database Testing
- **MongoDB Atlas IP Whitelist**: The running ChroniQ backend at `http://127.0.0.1:8000` requires adding the developer's current public IP address to the MongoDB Atlas Network Access whitelist.

---

## Deployment Readiness: Pre-Render Checklist

Before deploying this MCP server to Render and connecting to Healix:
1. **ChroniQ Backend Accessibility**: Deploy ChroniQ backend or make it reachable over public HTTPS, and configure `CHRONIQ_API_BASE_URL`.
2. **MongoDB Atlas Network Access**: Ensure the backend's hosting environment IP is whitelisted on MongoDB Atlas.
3. **Render Service Settings**:
   - Environment: Python 3.11+
   - Build Command: `pip install -e .`
   - Start Command: `python -m app.server` (Render automatically injects `PORT`)
   - Environment Variables:
     - `CHRONIQ_API_BASE_URL=https://<your-chroniq-backend-domain>`
     - `CHRONIQ_ENABLE_MUTATIONS=true` (or `false` for read-only preview)
     - `MCP_TRANSPORT=streamable-http`
     - `MCP_HOST=0.0.0.0`
4. **Healix Integration**: Point Healix MCP client to `https://<render-mcp-service-name>.onrender.com/mcp` with patient Bearer tokens passed in request headers.

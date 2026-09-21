# ChroniQ MCP Server

A standalone **Model Context Protocol (MCP) server** that exposes verified patient-facing ChroniQ healthcare features to the **Healix** AI assistant.

## Architecture

```
┌─────────────┐        MCP (stdio/SSE)        ┌───────────────┐        HTTP REST        ┌──────────────┐
│   Healix    │ ◄──────────────────────────► │  chroniq-mcp  │ ◄──────────────────────► │  ChroniQ     │
│ (AI Client) │                               │  MCP Server   │                          │  Backend     │
└─────────────┘                               └───────────────┘                          └──────┬───────┘
                                                                                                │
                                                                                         MongoDB Atlas
```

- **Separate project** — does not modify or run inside the ChroniQ backend or frontend.
- **HTTP only** — communicates with ChroniQ exclusively through its REST API.
- **No direct database access** — all authorization enforced by the ChroniQ backend.
- **Patient-facing only** — no staff, admin, doctor, kiosk, or auth tools exposed.

## Prerequisites

- Python 3.11+
- ChroniQ backend running and reachable at the configured URL
- A valid patient JWT access token

## Installation (no virtual environment)

```bash
cd chroniq-mcp
python -m pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `CHRONIQ_API_BASE_URL` | `http://127.0.0.1:8000` | ChroniQ backend URL |
| `CHRONIQ_REQUEST_TIMEOUT` | `15.0` | HTTP request timeout (seconds) |
| `CHRONIQ_CONNECT_TIMEOUT` | `5.0` | HTTP connection timeout (seconds) |
| `MCP_HOST` | `127.0.0.1` | MCP server bind host |
| `MCP_PORT` | `8001` | MCP server bind port |
| `CHRONIQ_ENABLE_MUTATIONS` | `false` | Enable write operations (disabled by default) |
| `CHRONIQ_AUTH_TOKEN` | *(empty)* | Dev-only: single-patient bearer token |

> **⚠ CHRONIQ_AUTH_TOKEN** is for local single-patient development only. Never set a shared admin/super-admin token. In production, use MCP session-scoped token forwarding.

## Running the MCP Server

```bash
python -m app.server
```

The server starts in **stdio transport** mode by default (suitable for local MCP clients like Claude Desktop, Cursor, etc.).

### MCP Client Configuration (Claude Desktop example)

Add to your MCP client configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "chroniq": {
      "command": "python",
      "args": ["-m", "app.server"],
      "cwd": "/path/to/chroniq-mcp",
      "env": {
        "CHRONIQ_API_BASE_URL": "http://127.0.0.1:8000",
        "CHRONIQ_AUTH_TOKEN": "<your-patient-jwt-token>",
        "CHRONIQ_ENABLE_MUTATIONS": "true"
      }
    }
  }
}
```

## Running Tests

```bash
python -m pytest tests/ -v
```

All tests use mocked HTTP responses — no production credentials or real patient data required.

## Authentication & Token Forwarding

ChroniQ uses **JWT (HS256) access tokens** for authentication. The MCP server:

1. **Accepts** the patient's access token via MCP session headers or the `CHRONIQ_AUTH_TOKEN` env var (dev only)
2. **Forwards** it as a `Bearer` token on every backend request
3. **Never** accepts patient_id, user_id, or role as tool arguments
4. **Never** decodes or trusts JWT claims for authorization — the backend validates everything
5. **Never** logs tokens, passwords, OTPs, or sensitive patient data

**Limitations:**
- The current stdio transport does not support per-session token injection. Each MCP server instance is bound to a single patient via `CHRONIQ_AUTH_TOKEN`.
- Multi-patient support requires a transport that supports per-request authentication headers (e.g. HTTP/SSE with session middleware).

## Deployed vs Local

> **⚠ Important:** A remotely deployed Healix instance **cannot** reach a ChroniQ backend bound only to `localhost` or `127.0.0.1`. For remote access, configure a secured, publicly reachable ChroniQ API endpoint with HTTPS.

## Tool Summary

**28 tools enabled** across 11 categories:

| Category | Tools | Auth |
|---|---|---|
| Discovery | `list_hospitals`, `get_hospital_details`, `search_doctors`, `get_doctor_profile`, `list_specialties` | No |
| Slots | `get_doctor_slots`, `hold_appointment_slot`, `release_appointment_slot` | Partial/Yes |
| Appointments | `book_appointment`, `list_my_appointments`, `get_appointment_details`, `cancel_appointment` | Yes |
| Patient | `get_patient_profile`, `update_patient_profile` | Yes |
| Family | `list_family_members`, `add_family_member`, `update_family_member`, `delete_family_member` | Yes |
| Documents | `list_medical_documents`, `update_medical_document` | Yes |
| Reviews | `list_my_reviews`, `submit_appointment_review`, `update_appointment_review` | Yes |
| Support | `list_support_tickets`, `create_support_ticket` | Yes |
| Notifications | `list_notifications`, `mark_notification_as_read` | Yes |
| Account | `update_notification_preferences` | Yes |

**8 tools blocked** (see [CHRONIQ_MCP_TOOL_CATALOG.md](CHRONIQ_MCP_TOOL_CATALOG.md) for details):
- `reschedule_appointment` — non-atomic multi-save
- `check_in_appointment` — no mandatory auth enforcement
- `get_patient_queue_status` — no auth/ownership
- `get_department_queue_board` — no auth, exposes appointment IDs
- `delete_medical_document` — physical file not removed
- `request_account_deletion` — no purge worker
- `cancel_account_deletion` — depends on deletion being enabled
- `export_patient_data` — leaks internal fields

## Mutation Safety

- **Mutations disabled by default** (`CHRONIQ_ENABLE_MUTATIONS=false`)
- **High-impact operations require explicit confirmation** (`confirmed=True`):
  - `hold_appointment_slot`, `book_appointment`, `cancel_appointment`
  - `delete_family_member`, `submit_appointment_review`
  - `create_support_ticket`
  - `update_patient_profile` (for phone/email changes only)

## Excluded Endpoint Categories

- Staff queue management (call-next, call-again, start/complete consultation, skip, no-show, emergency, priority)
- Doctor portal routes
- Hospital admin routes
- Super admin routes
- Kiosk routes
- Walk-in routes
- Authentication routes (login, register, OTP, password, OAuth, token refresh)
- SSE queue stream
- Health check endpoint
- Shared `GET /appointments` (use `/appointments/me`)
- Review-by-appointment endpoint
- Multipart document upload
- Any endpoint without verified patient authorization

## Known Backend Security Gaps

| Gap | Severity | Affected Tool | Issue |
|---|---|---|---|
| #1 | CRITICAL | `check_in_appointment` | `get_optional_user` — no auth enforcement |
| #2 | CRITICAL | `get_patient_queue_status` | No auth, no ownership check |
| #6 | HIGH | `reschedule_appointment` | Non-atomic multi-save without transaction |
| #9 | MEDIUM | `get_department_queue_board` | Exposes appointment IDs publicly |
| #13 | MEDIUM | `delete_medical_document` | Physical file not deleted from storage |
| #14 | MEDIUM | `request_account_deletion` | No purge worker exists |
| #15 | LOW | `list_notifications` | `body` vs `message` field mismatch (handled gracefully) |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Could not connect to ChroniQ" | Backend not running | Start the ChroniQ backend |
| "Mutations are disabled" | Safety gate active | Set `CHRONIQ_ENABLE_MUTATIONS=true` |
| "session may have expired" | JWT expired | Obtain a fresh access token |
| "Access denied" | Wrong role or ownership | Verify the token belongs to the correct patient |
| All mutations return disabled | Env var not set | Ensure `.env` file is in the working directory |

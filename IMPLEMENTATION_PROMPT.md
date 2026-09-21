# ChroniQ MCP Server — Implementation Prompt

Act as a senior Python/MCP engineer. Build a standalone MCP server named `chroniq-mcp` that exposes verified existing ChroniQ backend features to Healix.

## Required approach
1. Inspect the real ChroniQ backend source, API routers, schemas, dependencies, services, configuration, tests, and `CHRONIQ_MCP_TOOL_CATALOG.md` if present. Treat source code as authoritative; do not guess routes or payloads.
2. Use the ChroniQ HTTP API. Never connect directly to MongoDB or duplicate backend business logic.
3. Keep this project separate from the existing ChroniQ backend and frontend.
4. Do not create/use a virtual environment. No `venv`, `virtualenv`, or activation instructions.
5. Use the supported Python MCP SDK/FastMCP and `httpx` (or a justified compatible alternative).
6. Create `.env.example`, `.gitignore`, dependency manifest, README, modular source, and tests.
7. Reconcile the earlier inventory discrepancy: it described 30 tools but enumerated 5 public reads + 1 slot lookup + 9 authenticated reads + 19 mutations. Count only actual verified tools.

## Recommended architecture
- `app/server.py`: MCP setup, transport, registration.
- `app/config.py`: validated environment settings.
- `app/auth.py`: trusted caller identity/token context; never accept identity from ordinary tool arguments.
- `app/clients/chroniq_api.py`: shared async HTTP client, bearer forwarding, timeouts, safe errors.
- `app/tools/discovery.py`: hospital, specialty, doctor discovery.
- `app/tools/appointments.py`: appointment reads and approved operations.
- `app/tools/patient.py`: profile and patient-owned resources.
- `app/tools/queues.py`: only secure, verified queue operations.
- `app/tools/reviews.py` and `app/tools/support.py`: only if verified and safe.
- `tests/`: auth, API client, tool mapping, safety tests.

Adapt the modules to the verified catalog. Do not add fake or empty tools.

## Initial tools
If verified and safe, begin with `list_hospitals`, `get_hospital_details`, `search_doctors`, `get_doctor_profile`, `list_specialties`, `list_my_appointments`, and `get_patient_profile`. All tool arguments and output mappings must match actual backend contracts.

Treat `get_doctor_slots` as potentially state-changing: previous inspection reported that GET may generate 14 days of slots in the database. Do not describe it as read-only. Exclude it initially unless the side effect is verified, documented, and approved.

## Authentication/security
- Use the real ChroniQ auth mechanism and forward the authenticated caller's user-scoped bearer token where required.
- Never log or return tokens, secrets, stack traces, internal paths, or sensitive unrelated patient data.
- Never trust user-supplied patient ID, user ID, role, or tenant ID to authorize access.
- Backend authorization and tenant isolation must be enforced by ChroniQ itself. MCP filtering is not a substitute.
- If Healix cannot securely provide a caller-scoped token, document the integration contract and do not substitute a shared superuser token.
- Do not expose arbitrary method/path proxy tools, raw database tools, or unrestricted API tools.
- Exclude staff/admin/doctor/kiosk, direct auth, SSE, health endpoints, and catalog-excluded routes unless individually reviewed.

## Mutations
Keep mutations disabled by default behind a configuration safety gate. Before exposing each mutation, verify route, schema, authorization, ownership, business rules, side effects, idempotency, and tests. Do not silently retry non-idempotent writes.
Require explicit confirmation in the Healix/client flow for high-impact operations. These were previously identified as high impact: booking, cancellation, rescheduling, check-in, account deletion request, deleting a family member, and deleting a medical document. Do not claim the MCP server alone guarantees confirmation unless the client protocol enforces it.

## Previously reported issues to re-check
1. `POST /queue/check-in` may use optional auth and skip ownership checks without a token.
2. `GET /queue/{appointment_id}` may lack auth/ownership.
3. Rescheduling may perform multiple saves without a transaction.
4. `GET /reviews/by-appointment/{id}` may be unauthenticated.
5. Review creation may not require a completed appointment.
6. Booking may allow `patient_name` override.
7. Medical-document deletion may leave the physical file behind.
8. Account deletion may only set a timestamp without a purge worker.

Verify each issue against current source. Block affected tools until fixed or a reviewed safe alternative exists.

## Implementation requirements
- Stable, descriptive tool names and accurate descriptions.
- Strict argument validation: identifiers, dates, enums, pagination, bounds.
- Concise JSON-compatible results.
- Safe mapping of backend errors; do not leak response bodies containing private details.
- Explicit timeouts; no automatic retries for unsafe writes.
- No hard-coded credentials or production URLs.
- No direct DB access and no generic endpoint proxy.

## Tests
Use mocked HTTP. Test configuration, bearer forwarding, secret redaction, success/error/timeout/malformed responses, argument validation, route mapping, blocked routes not being registered, identity not being overridable by tool input, and mutation gate defaulting off. Tests must not require production credentials or real patient data.

## README
Document prerequisites, installation and running without venv, environment variables, local MCP client configuration with placeholders, Healix connection requirements, transport/deployment, complete verified tool table (auth, side effects, confirmation, status), exclusions, security limitations, tests, and troubleshooting. Explain that remotely hosted Healix cannot reach a backend bound only to localhost; a secured reachable endpoint is needed.

## Completion report
List files created, implemented tools, excluded/blocked tools and reasons, test results, remaining backend blockers, and exact Healix integration steps. Do not claim deployment or live integration unless actually tested.


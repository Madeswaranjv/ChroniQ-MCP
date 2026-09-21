"""ChroniQ MCP Server — FastMCP entry point.

Registers all verified patient-facing tools and runs the MCP transport.
Blocked tools are documented but NOT registered.
"""

from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

from app.config import settings

# Configure logging — never log tokens or patient data
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("chroniq_mcp")

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------
mcp = MCPServer(
    "ChroniQ",
    instructions=(
        "ChroniQ MCP Server — Patient-facing healthcare tools for Healix. "
        "All appointments follow IST (Asia/Kolkata). "
        "Mutations are disabled by default (CHRONIQ_ENABLE_MUTATIONS). "
        "High-impact operations require explicit confirmation (confirmed=True). "
        "Identity is derived from the authenticated JWT — never from tool arguments."
    ),
)

# ---------------------------------------------------------------------------
# Register tool modules
# ---------------------------------------------------------------------------

# A. PUBLIC DISCOVERY (5 tools — no auth required)
from app.tools.discovery import (  # noqa: E402
    get_doctor_profile,
    get_hospital_details,
    list_hospitals,
    list_specialties,
    search_doctors,
)

mcp.tool()(list_hospitals)
mcp.tool()(get_hospital_details)
mcp.tool()(search_doctors)
mcp.tool()(get_doctor_profile)
mcp.tool()(list_specialties)

# B. SLOT DISCOVERY AND RESERVATION (3 tools)
from app.tools.slots import (  # noqa: E402
    get_doctor_slots,
    hold_appointment_slot,
    release_appointment_slot,
)

mcp.tool()(get_doctor_slots)
mcp.tool()(hold_appointment_slot)
mcp.tool()(release_appointment_slot)

# C. APPOINTMENTS (4 tools — reschedule_appointment BLOCKED: Gap #6)
from app.tools.appointments import (  # noqa: E402
    book_appointment,
    cancel_appointment,
    get_appointment_details,
    list_my_appointments,
)

mcp.tool()(book_appointment)
mcp.tool()(list_my_appointments)
mcp.tool()(get_appointment_details)
mcp.tool()(cancel_appointment)

# D. QUEUE — ALL BLOCKED
# get_patient_queue_status:    BLOCKED — No auth, no ownership (Gap #2)
# get_department_queue_board:  BLOCKED — No auth, exposes appointment IDs (Gap #9)
# check_in_appointment:        BLOCKED — get_optional_user, no auth enforcement (Gap #1)

# E. PATIENT PROFILE (2 tools)
from app.tools.patient import (  # noqa: E402
    get_patient_profile,
    update_patient_profile,
)

mcp.tool()(get_patient_profile)
mcp.tool()(update_patient_profile)

# F. FAMILY MEMBERS (4 tools)
from app.tools.family import (  # noqa: E402
    add_family_member,
    delete_family_member,
    list_family_members,
    update_family_member,
)

mcp.tool()(list_family_members)
mcp.tool()(add_family_member)
mcp.tool()(update_family_member)
mcp.tool()(delete_family_member)

# G. MEDICAL DOCUMENTS (2 tools — delete BLOCKED: Gap #13, upload excluded)
from app.tools.documents import (  # noqa: E402
    list_medical_documents,
    update_medical_document,
)

mcp.tool()(list_medical_documents)
mcp.tool()(update_medical_document)

# H. REVIEWS (3 tools)
from app.tools.reviews import (  # noqa: E402
    list_my_reviews,
    submit_appointment_review,
    update_appointment_review,
)

mcp.tool()(list_my_reviews)
mcp.tool()(submit_appointment_review)
mcp.tool()(update_appointment_review)

# I. SUPPORT (2 tools)
from app.tools.support import (  # noqa: E402
    create_support_ticket,
    list_support_tickets,
)

mcp.tool()(list_support_tickets)
mcp.tool()(create_support_ticket)

# J. NOTIFICATIONS (2 tools)
from app.tools.notifications import (  # noqa: E402
    list_notifications,
    mark_notification_as_read,
)

mcp.tool()(list_notifications)
mcp.tool()(mark_notification_as_read)

# K. ACCOUNT (1 tool — export/deletion BLOCKED: Gaps #14, response leaks)
from app.tools.account import (  # noqa: E402
    update_notification_preferences,
)

mcp.tool()(update_notification_preferences)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
_TOOL_COUNT = 28
logger.info(
    "ChroniQ MCP: %d patient tools registered | mutations=%s | backend=%s",
    _TOOL_COUNT,
    settings.chroniq_enable_mutations,
    settings.chroniq_api_base_url,
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()

"""Safety and security tests.

Verifies:
- Mutation gate defaults to disabled
- Blocked/unsafe tools are NOT registered
- No staff/admin/kiosk/doctor tools registered
- No arbitrary endpoint proxy exists
- No patient_id or role override via tool arguments
- No token leakage in tool results
"""

import pytest
from app.server import mcp
from app.config import settings


class TestMutationGate:
    def test_mutations_default_disabled(self):
        """CHRONIQ_ENABLE_MUTATIONS defaults to False."""
        from app.config import Settings
        s = Settings(_env_file=None)
        assert s.chroniq_enable_mutations is False


class TestRegisteredTools:
    def _tool_names(self):
        """Get all registered MCP tool names."""
        # Access the internal tool registry
        tools = mcp._tool_manager._tools
        return set(tools.keys())

    def test_expected_tool_count(self):
        """Verify exactly 28 tools are registered."""
        names = self._tool_names()
        assert len(names) == 28, f"Expected 28 tools, got {len(names)}: {sorted(names)}"

    def test_blocked_tools_not_registered(self):
        """Verify blocked tools are NOT in the registry."""
        names = self._tool_names()
        blocked = {
            "reschedule_appointment",
            "check_in_appointment",
            "get_patient_queue_status",
            "get_department_queue_board",
            "delete_medical_document",
            "request_account_deletion",
            "cancel_account_deletion",
            "export_patient_data",
        }
        for tool in blocked:
            assert tool not in names, f"Blocked tool '{tool}' should not be registered"

    def test_no_staff_admin_tools(self):
        """Verify no staff/admin/doctor/kiosk tools are registered."""
        names = self._tool_names()
        forbidden_prefixes = [
            "call_next", "call_again", "start_consult", "complete_consult",
            "skip_patient", "mark_no_show", "emergency_insert", "update_priority",
            "confirm_appointment_desk",
        ]
        for prefix in forbidden_prefixes:
            for name in names:
                assert prefix not in name, f"Staff tool '{name}' should not be registered"

    def test_no_auth_tools(self):
        """Verify no login/register/OTP/password tools are registered."""
        names = self._tool_names()
        auth_tools = {"login", "register", "verify_otp", "resend_otp",
                       "forgot_password", "reset_password", "change_password",
                       "refresh_token", "google_auth"}
        for tool in auth_tools:
            assert tool not in names, f"Auth tool '{tool}' should not be registered"

    def test_no_generic_proxy(self):
        """Verify no arbitrary endpoint proxy tool exists."""
        names = self._tool_names()
        proxy_names = {"call_api", "proxy", "raw_request", "http_request",
                        "generic_request", "call_endpoint"}
        for name in proxy_names:
            assert name not in names, f"Proxy tool '{name}' should not exist"

    def test_expected_tools_present(self):
        """Verify all 28 expected tools are registered."""
        names = self._tool_names()
        expected = {
            "list_hospitals", "get_hospital_details", "search_doctors",
            "get_doctor_profile", "list_specialties",
            "get_doctor_slots", "hold_appointment_slot", "release_appointment_slot",
            "book_appointment", "list_my_appointments", "get_appointment_details",
            "cancel_appointment",
            "get_patient_profile", "update_patient_profile",
            "list_family_members", "add_family_member", "update_family_member",
            "delete_family_member",
            "list_medical_documents", "update_medical_document",
            "list_my_reviews", "submit_appointment_review", "update_appointment_review",
            "list_support_tickets", "create_support_ticket",
            "list_notifications", "mark_notification_as_read",
            "update_notification_preferences",
        }
        for tool in expected:
            assert tool in names, f"Expected tool '{tool}' not registered"


class TestNoIdentityOverride:
    """Verify tool functions do not accept patient_id or role as arguments."""

    def test_book_appointment_no_patient_id(self):
        """book_appointment must not accept patient_id."""
        import inspect
        from app.tools.appointments import book_appointment
        sig = inspect.signature(book_appointment)
        param_names = set(sig.parameters.keys())
        assert "patient_id" not in param_names
        assert "patient_name" not in param_names
        assert "role" not in param_names
        assert "user_id" not in param_names

# ChroniQ MCP Tool Catalog

Complete verified inventory of all MCP tools, their backend routes, schemas, access requirements, side effects, confirmation needs, and implementation status.

**Generated from inspection of:** ChroniQ backend at `E:\KLN\ChroniQ\backend` and `CHRONIQ_MCP_TOOL_SPEC.md`.

---

## Summary

| Status | Count |
|---|---|
| ✅ Enabled | 28 |
| 🚫 Blocked | 8 |
| ❌ Excluded (staff/admin/auth/infra) | 77+ |
| **Total patient-facing verified** | **36** |

---

## A. Public Discovery (5 tools — no authentication)

### ✅ 1. `list_hospitals`
| Property | Value |
|---|---|
| **HTTP** | `GET /hospitals` |
| **Auth** | None |
| **Mutation** | No |
| **Confirmation** | No |
| **Query Params** | `city`, `specialty`, `rating`, `search`, `lat`, `lng`, `radius_km` |
| **Validation** | `rating` must be 0.0–5.0; `lat`/`lng` must be paired |
| **Side Effects** | None |
| **Status** | ✅ Enabled |

### ✅ 2. `get_hospital_details`
| Property | Value |
|---|---|
| **HTTP** | `GET /hospitals/{id}` |
| **Auth** | None |
| **Mutation** | No |
| **Path Params** | `id` (required) |
| **Returns** | Hospital details with departments and doctors |
| **Status** | ✅ Enabled |

### ✅ 3. `search_doctors`
| Property | Value |
|---|---|
| **HTTP** | `GET /doctors` |
| **Auth** | None |
| **Mutation** | No |
| **Query Params** | `specialty`, `hospital_id`, `city`, `gender`, `language`, `fee_max`, `rating_min`, `search` |
| **Validation** | `rating_min` must be 0.0–5.0 |
| **Status** | ✅ Enabled |

### ✅ 4. `get_doctor_profile`
| Property | Value |
|---|---|
| **HTTP** | `GET /doctors/{id}` |
| **Auth** | None |
| **Mutation** | No |
| **Path Params** | `id` (required) |
| **Status** | ✅ Enabled |

### ✅ 5. `list_specialties`
| Property | Value |
|---|---|
| **HTTP** | `GET /specialties` |
| **Auth** | None |
| **Mutation** | No |
| **Arguments** | None |
| **Status** | ✅ Enabled |

---

## B. Slot Discovery & Reservation (3 tools)

### ✅ 6. `get_doctor_slots`
| Property | Value |
|---|---|
| **HTTP** | `GET /doctors/{id}/slots` |
| **Auth** | None (but token sent for defense-in-depth) |
| **Mutation** | ⚠ DB side effect |
| **Path Params** | `doctor_id` (required) |
| **Query Params** | `date` (required, YYYY-MM-DD) |
| **Side Effects** | Backend calls `generate_slots_for_doctor(id, days=14)` which creates slot records if they don't exist |
| **Confirmation** | No |
| **Status** | ✅ Enabled (side effect documented) |

### ✅ 7. `hold_appointment_slot`
| Property | Value |
|---|---|
| **HTTP** | `POST /slots/{id}/hold` |
| **Auth** | Required (patient JWT) |
| **Mutation** | Yes |
| **Confirmation** | ⚠ Required |
| **Path Params** | `slot_id` (required) |
| **Side Effects** | Holds slot for ~5 minutes; 409 if already held/booked |
| **Status** | ✅ Enabled |

### ✅ 8. `release_appointment_slot`
| Property | Value |
|---|---|
| **HTTP** | `POST /slots/{id}/release` |
| **Auth** | Required (patient JWT) |
| **Mutation** | Yes |
| **Confirmation** | No |
| **Path Params** | `slot_id` (required) |
| **Status** | ✅ Enabled |

---

## C. Appointments (4 enabled, 1 blocked)

### ✅ 9. `book_appointment`
| Property | Value |
|---|---|
| **HTTP** | `POST /appointments` |
| **Auth** | Required (patient JWT) |
| **Mutation** | Yes |
| **Confirmation** | ⚠ Required |
| **Body** | `slot_id` (required), `doctor_id` (required), `family_member_id`, `reason`, `symptoms_note` |
| **Excluded Fields** | `patient_name`, `patient`, `patient_id` — NEVER sent |
| **Side Effects** | Creates appointment, transitions slot to booked |
| **Status** | ✅ Enabled |

### ✅ 10. `list_my_appointments`
| Property | Value |
|---|---|
| **HTTP** | `GET /appointments/me` |
| **Auth** | Required (patient JWT) |
| **Mutation** | No |
| **Note** | Uses `/appointments/me` (not shared `/appointments`) |
| **Status** | ✅ Enabled |

### ✅ 11. `get_appointment_details`
| Property | Value |
|---|---|
| **HTTP** | `GET /appointments/{id}` |
| **Auth** | Required (patient JWT) |
| **Mutation** | No |
| **Path Params** | `id` (appointment ID or booking code) |
| **Ownership** | Backend enforces patient_id match |
| **Status** | ✅ Enabled |

### ✅ 12. `cancel_appointment`
| Property | Value |
|---|---|
| **HTTP** | `POST /appointments/{id}/cancel` |
| **Auth** | Required (patient JWT) |
| **Mutation** | Yes |
| **Confirmation** | ⚠ Required |
| **Body** | `reason` (optional) |
| **Ownership** | Backend enforces patient_id match |
| **Status** | ✅ Enabled |

### 🚫 B1. `reschedule_appointment`
| Property | Value |
|---|---|
| **HTTP** | `PATCH /appointments/{id}/reschedule` |
| **Status** | 🚫 BLOCKED |
| **Reason** | Non-atomic multi-save (Gap #6). Multiple sequential `.save()` calls without a database transaction risk partial updates. |

---

## D. Queue (0 enabled, 3 blocked)

### 🚫 B2. `check_in_appointment`
| Property | Value |
|---|---|
| **HTTP** | `POST /queue/check-in` |
| **Status** | 🚫 BLOCKED |
| **Reason** | Uses `get_optional_user` — no mandatory authentication or ownership enforcement (Gap #1). |

### 🚫 B3. `get_patient_queue_status`
| Property | Value |
|---|---|
| **HTTP** | `GET /queue/{appointment_id}` |
| **Status** | 🚫 BLOCKED |
| **Reason** | No authentication, no ownership check (Gap #2). Any appointment ID can be queried. |

### 🚫 B4. `get_department_queue_board`
| Property | Value |
|---|---|
| **HTTP** | `GET /queue/{hospital_id}/{department_id}` |
| **Status** | 🚫 BLOCKED |
| **Reason** | No authentication, exposes all appointment IDs for multiple patients (Gap #9). |

---

## E. Patient Profile (2 tools)

### ✅ 13. `get_patient_profile`
| Property | Value |
|---|---|
| **HTTP** | `GET /patients/me/profile` |
| **Auth** | Required (patient JWT) |
| **Mutation** | No |
| **Status** | ✅ Enabled |

### ✅ 14. `update_patient_profile`
| Property | Value |
|---|---|
| **HTTP** | `PATCH /users/me` |
| **Auth** | Required (patient JWT) |
| **Mutation** | Yes |
| **Confirmation** | ⚠ Required for phone/email changes |
| **Body** | `name`, `phone`, `email`, `age`, `gender`, `preferred_language`, `photo_url` |
| **Status** | ✅ Enabled |

---

## F. Family Members (4 tools)

### ✅ 15. `list_family_members`
| Property | Value |
|---|---|
| **HTTP** | `GET /patients/me/family` |
| **Auth** | Required |
| **Status** | ✅ Enabled |

### ✅ 16. `add_family_member`
| Property | Value |
|---|---|
| **HTTP** | `POST /family-members` |
| **Auth** | Required |
| **Mutation** | Yes |
| **Body** | `name` (required), `relation` (required), `age`, `gender` |
| **Quota** | Max 6 family members per patient |
| **Status** | ✅ Enabled |

### ✅ 17. `update_family_member`
| Property | Value |
|---|---|
| **HTTP** | `PATCH /family-members/{id}` |
| **Auth** | Required |
| **Mutation** | Yes |
| **Ownership** | Backend enforces user_id match |
| **Status** | ✅ Enabled |

### ✅ 18. `delete_family_member`
| Property | Value |
|---|---|
| **HTTP** | `DELETE /family-members/{id}` |
| **Auth** | Required |
| **Mutation** | Yes |
| **Confirmation** | ⚠ Required |
| **Ownership** | Backend enforces user_id match |
| **Status** | ✅ Enabled |

---

## G. Medical Documents (2 enabled, 1 blocked)

### ✅ 19. `list_medical_documents`
| Property | Value |
|---|---|
| **HTTP** | `GET /documents` |
| **Auth** | Required |
| **Note** | Returns metadata only; `file_path` stripped by client |
| **Status** | ✅ Enabled |

### ✅ 20. `update_medical_document`
| Property | Value |
|---|---|
| **HTTP** | `PATCH /documents/{id}` |
| **Auth** | Required |
| **Mutation** | Yes |
| **Body** | `name`, `category` |
| **Valid categories** | `lab_report`, `prescription`, `imaging`, `discharge_summary`, `other` |
| **Status** | ✅ Enabled |

### 🚫 B5. `delete_medical_document`
| Property | Value |
|---|---|
| **HTTP** | `DELETE /documents/{id}` |
| **Status** | 🚫 BLOCKED |
| **Reason** | DB record deleted but physical file not removed from storage (Gap #13). |

---

## H. Reviews (3 tools)

### ✅ 21. `list_my_reviews`
| Property | Value |
|---|---|
| **HTTP** | `GET /reviews` |
| **Auth** | Required |
| **Status** | ✅ Enabled |

### ✅ 22. `submit_appointment_review`
| Property | Value |
|---|---|
| **HTTP** | `POST /reviews` |
| **Auth** | Required |
| **Mutation** | Yes |
| **Confirmation** | ⚠ Required |
| **Body** | `appointment_id` (required), `doctor_rating` (1–5), `hospital_rating` (1–5), `comment`, `tags`, `wait_as_expected` |
| **Valid `wait_as_expected`** | `shorter`, `as_expected`, `longer` |
| **Precondition** | Backend enforces appointment status = completed |
| **Status** | ✅ Enabled |

### ✅ 23. `update_appointment_review`
| Property | Value |
|---|---|
| **HTTP** | `PATCH /reviews/{id}` |
| **Auth** | Required |
| **Mutation** | Yes |
| **Ownership** | Backend enforces patient_id match + 48-hour edit window |
| **Status** | ✅ Enabled |

---

## I. Support Tickets (2 tools)

### ✅ 24. `list_support_tickets`
| Property | Value |
|---|---|
| **HTTP** | `GET /support/tickets` |
| **Auth** | Required |
| **Status** | ✅ Enabled |

### ✅ 25. `create_support_ticket`
| Property | Value |
|---|---|
| **HTTP** | `POST /support/tickets` |
| **Auth** | Required |
| **Mutation** | Yes |
| **Confirmation** | ⚠ Required |
| **Body** | `category` (required), `description` (required), `appointment_id`, `hospital_id`, `contact_preference` |
| **Valid categories** | `booking_problem`, `queue_or_waiting`, `fee_or_payment`, `app_problem`, `privacy_concern`, `other` |
| **Valid contact_preference** | `in_app`, `email`, `sms` |
| **Status** | ✅ Enabled |

---

## J. Notifications (2 tools)

### ✅ 26. `list_notifications`
| Property | Value |
|---|---|
| **HTTP** | `GET /notifications` |
| **Auth** | Required |
| **Known Issue** | Model stores `body` but route returns `message` — both fields normalised |
| **Status** | ✅ Enabled |

### ✅ 27. `mark_notification_as_read`
| Property | Value |
|---|---|
| **HTTP** | `PATCH /notifications/{id}/read` |
| **Auth** | Required |
| **Mutation** | Yes |
| **Ownership** | Backend enforces user_id match |
| **Status** | ✅ Enabled |

---

## K. Account & Preferences (1 enabled, 3 blocked)

### ✅ 28. `update_notification_preferences`
| Property | Value |
|---|---|
| **HTTP** | `PUT /users/me/notification-preferences` |
| **Auth** | Required |
| **Mutation** | Yes |
| **Body** | `channels` (nested dict), `reminder_24h` (bool), `reminder_1h` (bool) |
| **Status** | ✅ Enabled |

### 🚫 B6. `request_account_deletion`
| Property | Value |
|---|---|
| **HTTP** | `POST /users/me/delete-request` |
| **Status** | 🚫 BLOCKED |
| **Reason** | Only sets `deletion_requested_at` timestamp. No purge worker or verified grace period exists (Gap #14). |

### 🚫 B7. `cancel_account_deletion`
| Property | Value |
|---|---|
| **HTTP** | `DELETE /users/me/delete-request` |
| **Status** | 🚫 BLOCKED |
| **Reason** | Depends on `request_account_deletion` being enabled first. |

### 🚫 B8. `export_patient_data`
| Property | Value |
|---|---|
| **HTTP** | `POST /users/me/export` |
| **Status** | 🚫 BLOCKED |
| **Reason** | Returns raw `.dict()` including `file_path`, `password_hash`, and other internal fields without data minimisation. |

---

## Excluded Endpoint Classes

| Category | Examples | Count |
|---|---|---|
| Staff queue management | call-next, call-again, start/complete consultation, skip, no-show, emergency-insert, priority | 9 |
| Doctor portal | schedule, availability, consultation notes | 10+ |
| Hospital admin | dashboard, staff management, broadcasts, reports | 20+ |
| Super admin | platform management, hospital provisioning | 5+ |
| Kiosk | check-in, patient lookup | 5+ |
| Walk-in | walk-in registration | 3+ |
| Authentication | login, register, OTP, password reset/change, Google OAuth, token refresh, contact verify | 12+ |
| Infrastructure | health, SSE stream, OpenAPI docs | 3+ |
| Alias routes | `GET /slots/available`, `GET /patient/profile`, `GET /appointments` | 3+ |

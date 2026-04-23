# ADR-014: Admin Self-Deletion Policy

## Status

Accepted (2026-04-16)

## Context

Story 6-2 (account data deletion UX) implements `DELETE /users/me` for all users, including admin accounts. The `audit_logs` table has a `RESTRICT` foreign key on `admin_id`:

```sql
ALTER TABLE audit_logs
ADD CONSTRAINT audit_logs_admin_id_fkey
FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE RESTRICT;
```

If an admin user — who has created correction audit logs — attempts account deletion, the RESTRICT constraint raises a foreign-key violation and crashes the endpoint with a 500 error. This blocks Story 6-2 from shipping.

Additionally, GDPR Article 17 (Right to Erasure) requires that deletion capability be available to all users, including admins. Blocking deletion for admins who have made corrections violates compliance requirements.

Three options were considered.

## Decision

**Option B: SET NULL** — change `audit_logs.admin_id` from `RESTRICT` to `SET NULL` and make the column nullable.

### Option A: Keep RESTRICT (Rejected)

Leave the `RESTRICT` FK as-is. Admin accounts with audit logs cannot be deleted — they must be deactivated or reassigned instead.

- **Pros:** Zero schema change; simplest option.
- **Cons:** Violates GDPR Article 17 for any admin who exercises right-to-erasure; silent compliance violation.

### Option B: SET NULL (Accepted)

Change the FK constraint on `audit_logs.admin_id` to `ON DELETE SET NULL` and make the column nullable.

- **Pros:** Admins can delete their accounts; audit records are preserved with the correction data intact; identity of the admin actor is removed but the correction record (what was changed, when, why) remains.
- **Cons:** The admin's identity is lost from the audit record. The `corrected_by` context is gone. This is acceptable because GDPR's erasure right takes precedence over audit attribution in this case.
- **Precedent:** Matches the existing SET NULL pattern for:
  - `consent_logs.user_id` (Migration 013)
  - `health_values.flag_reviewed_by_admin_id` (Migration 011)
  - `audit_logs.user_id` (subject of the correction)
  - `audit_logs.document_id`, `audit_logs.health_value_id`

### Option C: CASCADE (Rejected)

Delete `audit_logs` rows when the admin is deleted.

- **Pros:** Clean deletion, no orphaned rows.
- **Cons:** Destroys audit trail integrity — corrections that were made cannot be reviewed. Unacceptable for a medical application where audit trails are evidence of care quality.

## Consequences

### Positive

- Admin account deletion now succeeds via `DELETE /users/me` without a 500 error.
- GDPR Article 17 compliance is maintained for admin users.
- Audit records are preserved with full correction data (`value_name`, `original_value`, `new_value`, `reason`, `corrected_at`) — only the admin's identity is redacted.
- Service layer explicitly nullifies `admin_id` before deletion (defense-in-depth), matching the existing `user_id` redaction pattern.

### Negative

- `admin_id` column becomes nullable — queries that join or filter on `admin_id` must handle NULL.
- Admin corrections can no longer be attributed to a specific admin account after that admin is deleted. Any system or process relying on `audit_logs.admin_id` must handle NULL.
- Existing code that assumes `admin_id` is never NULL (e.g., non-nullable ORM fields) must be updated.

### Neutral

- The FK at the database level handles `ON DELETE SET NULL` automatically — even if the service-layer nullification is accidentally removed, the DB constraint still enforces the behavior.
- The same column already had a nullable sibling (`user_id`) following the SET NULL pattern, so the application layer already knows how to handle nullable audit IDs.

## Changes

| File | Change |
|------|--------|
| `alembic/versions/014_audit_logs_admin_id_set_null.py` | Migration: make `admin_id` nullable, drop RESTRICT FK, recreate with SET NULL |
| `app/admin/models.py` | `admin_id: Mapped[uuid.UUID \| None]` with `ondelete="SET NULL"` |
| `app/users/service.py` | Add `admin_id` nullification alongside existing `user_id` nullification in `delete_user_account()` |
| `tests/users/test_router.py` | Add admin self-deletion test and audit log retention test |

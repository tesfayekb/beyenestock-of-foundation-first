# Plan Changelog

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Tracks every plan revision with superseded-by linkage for historical tracing.

## Scope

All changes to `master-plan.md` and `approved-decisions.md`.

## Changelog Format

Each entry includes:
- **Section ID** changed
- **What** changed
- **Why** it changed
- **What stayed** unchanged
- **What was added**
- **What was removed**
- **Approval status**
- **Superseded-by** link (for changed approved sections)

## Entries

### v0 → v1 (2026-04-08)

**Type:** Initial creation

| Field | Value |
|-------|-------|
| Section IDs Created | PLAN-GOV-001, PLAN-AUTH-001, PLAN-RBAC-001, PLAN-USRMGMT-001, PLAN-ADMIN-001, PLAN-USRPNL-001, PLAN-AUDIT-001, PLAN-HEALTH-001, PLAN-API-001, PLAN-JOBS-001 |
| What Changed | Initial plan created |
| Why | Project initialization |
| What Stayed | N/A (first version) |
| What Was Added | All sections |
| What Was Removed | Nothing |
| Approval Status | PLAN-GOV-001: implemented; all others: proposed |
| Superseded Sections | None |

## Supersession Chain Template

For future entries where approved sections change:

```
| prior_section_id | PLAN-XXX-NNN |
| superseded_by    | PLAN-XXX-NNN (new) |
| date             | YYYY-MM-DD |
| reason           | [documented reason] |
```

## Dependencies

- [Master Plan](master-plan.md)
- [Approved Decisions](approved-decisions.md)

## Used By / Affects

Plan governance, historical tracing.

## Related Documents

- [Master Plan](master-plan.md)
- [Plan Review Log](plan-review-log.md)

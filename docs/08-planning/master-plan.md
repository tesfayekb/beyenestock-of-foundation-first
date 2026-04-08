# Master Plan

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

The canonical plan for this project. Every section has a stable ID and a status. This is the approved baseline for execution.

## Scope

All planned work across all modules.

## Plan Status Legend

| Status | Meaning |
|--------|---------|
| `proposed` | Under consideration, not yet reviewed |
| `approved` | Reviewed and approved for execution |
| `approved-partial` | Subsection approved, sibling subsections pending |
| `approved-with-modifications` | Approved with noted changes from original proposal |
| `deferred` | Intentionally postponed |
| `rejected` | Reviewed and rejected |
| `implemented` | Completed and verified |

## Plan Sections

### PLAN-GOV-001: SSOT Documentation System
**Status:** `implemented`
Create the 42-file SSOT documentation system with full governance, architecture, security, performance, module, quality, tracking, reference, and planning documentation.

### PLAN-AUTH-001: Authentication Module
**Status:** `proposed`
Implement email/password, Google OAuth, Apple Sign-In, and MFA using Lovable Cloud authentication.

### PLAN-RBAC-001: RBAC Module
**Status:** `proposed`
Implement role-based access control with `user_roles` table, `has_role()` security definer function, and RLS policies.

### PLAN-USRMGMT-001: User Management Module
**Status:** `proposed`
Implement user profiles, account settings, user listing, and account lifecycle management.

### PLAN-ADMIN-001: Admin Panel
**Status:** `proposed`
Build admin interface for user management, role management, audit log viewing, system health, and configuration.

### PLAN-USRPNL-001: User Panel
**Status:** `proposed`
Build user self-service interface for profile, settings, MFA, and session management.

### PLAN-AUDIT-001: Audit Logging
**Status:** `proposed`
Implement audit trail with immutable logs for all significant actions.

### PLAN-HEALTH-001: Health Monitoring
**Status:** `proposed`
Implement health checks, metrics tracking, and alerting.

### PLAN-API-001: API Layer
**Status:** `proposed`
Implement API conventions, error handling, edge function patterns, and input validation.

### PLAN-JOBS-001: Jobs and Scheduler
**Status:** `proposed`
Implement background job system with scheduling, retry logic, and failure handling.

## Execution Rules

- Only sections in `approved` or `approved-partial` status may be executed (Constitution Rule 9)
- Revisions merge into this baseline (Constitution Rule 10)
- Approved sections preserved unless explicitly superseded (Constitution Rule 8)

## Dependencies

- [Constitution](../00-governance/constitution.md)
- [System State](../00-governance/system-state.md)

## Used By / Affects

All execution decisions. AI Operating Model mandatory reading.

## Related Documents

- [Approved Decisions](approved-decisions.md)
- [Plan Changelog](plan-changelog.md)
- [Plan Review Log](plan-review-log.md)

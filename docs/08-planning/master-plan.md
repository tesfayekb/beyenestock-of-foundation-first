# Master Plan

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

## Purpose

The canonical plan for this project.
Every section has a stable ID, defined scope, dependencies, and execution criteria.

This document is the approved baseline for execution.

## Plan Status Legend

| Status | Meaning |
|--------|---------|
| `proposed` | Under consideration |
| `approved` | Ready for execution |
| `approved-partial` | Subsections approved |
| `approved-with-modifications` | Approved with changes |
| `deferred` | Postponed |
| `rejected` | Not accepted |
| `implemented` | Completed and verified |

## Plan Sections

---

### PLAN-GOV-001: SSOT Documentation System
**Status:** `implemented`
**Risk Level:** HIGH

**Purpose:**
Create full SSOT documentation system.

**Dependencies:** None
**Used By / Affects:** All modules

**Acceptance Criteria:**
- All governance, architecture, module, tracking, and planning docs exist
- Governance layer fully enforced

---

### PLAN-AUTH-001: Authentication Module
**Status:** `approved`
**Risk Level:** HIGH
**Module Doc:** [auth.md](../04-modules/auth.md)

**Purpose:**
Implement authentication system.

**Dependencies:**
- PLAN-GOV-001

**Used By / Affects:**
- RBAC
- User Management
- Admin Panel
- User Panel

**Subsections:**
- PLAN-AUTH-001-A: Email/Password
- PLAN-AUTH-001-B: Google OAuth
- PLAN-AUTH-001-C: Apple Sign-In
- PLAN-AUTH-001-D: MFA (Authenticator)

**Acceptance Criteria:**
- Secure login/logout
- MFA enforced for admin roles
- Session management implemented

---

### PLAN-RBAC-001: RBAC Module
**Status:** `approved`
**Risk Level:** HIGH
**Module Doc:** [rbac.md](../04-modules/rbac.md)

**Purpose:**
Implement role-based access control.

**Dependencies:**
- PLAN-AUTH-001

**Used By / Affects:**
- Admin Panel
- API
- User Management

**Acceptance Criteria:**
- Dynamic roles and permissions
- Secure enforcement at backend
- No UI-only authorization

---

### PLAN-USRMGMT-001: User Management Module
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [user-management.md](../04-modules/user-management.md)

**Dependencies:**
- PLAN-AUTH-001
- PLAN-RBAC-001

**Used By / Affects:**
- Admin Panel
- User Panel

**Acceptance Criteria:**
- User CRUD
- Account lifecycle management

---

### PLAN-ADMIN-001: Admin Panel
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [admin-panel.md](../04-modules/admin-panel.md)

**Dependencies:**
- PLAN-AUTH-001
- PLAN-RBAC-001

**Used By / Affects:**
- All modules

**Acceptance Criteria:**
- User management interface
- Role management interface
- Audit log viewing
- System health dashboard

---

### PLAN-USRPNL-001: User Panel
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [user-panel.md](../04-modules/user-panel.md)

**Dependencies:**
- PLAN-AUTH-001

**Acceptance Criteria:**
- Profile management
- Settings and MFA configuration
- Session management

---

### PLAN-AUDIT-001: Audit Logging
**Status:** `approved`
**Risk Level:** HIGH
**Module Doc:** [audit-logging.md](../04-modules/audit-logging.md)

**Dependencies:**
- PLAN-AUTH-001
- PLAN-RBAC-001

**Acceptance Criteria:**
- Immutable audit trail
- All significant actions logged
- Admin-viewable logs

---

### PLAN-HEALTH-001: Health Monitoring
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [health-monitoring.md](../04-modules/health-monitoring.md)

**Dependencies:** None

**Acceptance Criteria:**
- Health checks operational
- Metrics tracking active
- Alerting configured

---

### PLAN-API-001: API Layer
**Status:** `approved`
**Risk Level:** HIGH
**Module Doc:** [api.md](../04-modules/api.md)

**Dependencies:**
- PLAN-AUTH-001
- PLAN-RBAC-001

**Acceptance Criteria:**
- Consistent API conventions
- Error handling standardized
- Input validation enforced

---

### PLAN-JOBS-001: Jobs and Scheduler
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [jobs-and-scheduler.md](../04-modules/jobs-and-scheduler.md)

**Dependencies:** None

**Acceptance Criteria:**
- Job scheduling operational
- Retry logic implemented
- Failure handling defined

---

## Execution Order

Based on dependency chains:

1. ~~PLAN-GOV-001~~ (implemented)
2. PLAN-AUTH-001
3. PLAN-RBAC-001
4. PLAN-USRMGMT-001, PLAN-AUDIT-001, PLAN-API-001 (parallel after RBAC)
5. PLAN-ADMIN-001 (after RBAC + User Management)
6. PLAN-USRPNL-001 (after Auth)
7. PLAN-HEALTH-001, PLAN-JOBS-001 (independent, any time after GOV)

## Execution Rules

- Only `approved` or `approved-partial` sections may be executed
- Execution must follow dependency order
- No execution outside approved baseline
- All changes must follow [change-control-policy.md](../00-governance/change-control-policy.md)

## Dependencies

- [Constitution](../00-governance/constitution.md)
- [System State](../00-governance/system-state.md)

## Used By / Affects

All implementation and execution decisions.

## Related Documents

- [Approved Decisions](approved-decisions.md)
- [Plan Changelog](plan-changelog.md)
- [Plan Review Log](plan-review-log.md)

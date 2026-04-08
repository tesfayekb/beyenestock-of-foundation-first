# Approved Decisions

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Anti-forgetting ledger.
Every approved decision is recorded here with a stable ID.

This document is the authoritative memory for all approved architecture, security, and system rules.

## Scope

All approved decisions across the project lifecycle.

## Decision Record Format (MANDATORY)

Each decision MUST include:

- **Decision ID**
- **Plan Section**
- **Decision Type** (architecture / security / schema / policy / feature)
- **Date Approved**
- **Decision**
- **Affected Modules / Systems**
- **Status** (active / implemented / superseded)
- **Superseded By**

If any field is missing → the decision is **INVALID**.

## Decision Records

---

### DEC-001: SSOT Documentation System
- **Plan Section:** PLAN-GOV-001
- **Decision Type:** architecture
- **Date Approved:** 2026-04-08
- **Decision:** Create a 42-file SSOT documentation system across 9 directories with full governance, plan preservation, stable IDs, execution lock, and merge rules.
- **Affected Modules / Systems:** All
- **Status:** implemented
- **Superseded By:** —

---

### DEC-002: 10 Constitutional Rules
- **Plan Section:** PLAN-GOV-001
- **Decision Type:** policy
- **Date Approved:** 2026-04-08
- **Decision:** Constitution contains 10 non-negotiable rules including documentation phase lock, shared component protection, no silent behavior change, approved plan preservation, execution lock, and plan merge rule.
- **Affected Modules / Systems:** All
- **Status:** superseded
- **Superseded By:** DEC-006

---

### DEC-003: Feature Scope Lock
- **Plan Section:** PLAN-GOV-001
- **Decision Type:** policy
- **Date Approved:** 2026-04-08
- **Decision:** Feature scope locked to: Authentication (email + social + MFA), RBAC (dynamic permissions), Admin panel + User panel, Audit logging + Health monitoring, API layer, Background jobs / scheduler. No scope expansion without explicit approval.
- **Affected Modules / Systems:** All modules
- **Status:** active
- **Superseded By:** —

---

### DEC-004: Roles in Separate Table
- **Plan Section:** PLAN-RBAC-001
- **Decision Type:** schema
- **Date Approved:** 2026-04-08
- **Decision:** User roles MUST be stored in a separate `user_roles` table, never on the profile or users table. Security definer function `has_role()` used for all permission checks.
- **Affected Modules / Systems:** RBAC, Auth, API
- **Status:** active
- **Superseded By:** —

---

### DEC-005: Stable ID Convention
- **Plan Section:** PLAN-GOV-001
- **Decision Type:** policy
- **Date Approved:** 2026-04-08
- **Decision:** Plan sections use `PLAN-{MODULE}-{NNN}` format. Decisions use `DEC-{NNN}` format. IDs are permanent and never reassigned.
- **Affected Modules / Systems:** All
- **Status:** active
- **Superseded By:** —

---

### DEC-006: 11 Constitutional Rules
- **Plan Section:** PLAN-GOV-001
- **Decision Type:** policy
- **Date Approved:** 2026-04-08
- **Decision:** Constitution contains 11 non-negotiable rules including documentation phase lock, shared component protection, no silent behavior change, approved plan preservation, execution lock, plan merge rule, and Rule 11: Critical Module Override. Supersedes DEC-002 which referenced 10 rules.
- **Affected Modules / Systems:** All
- **Status:** active
- **Superseded By:** —

---

### DEC-007: Audit Log Retention Period — 90 Days
- **Plan Section:** PLAN-AUDIT-001
- **Decision Type:** policy
- **Date Approved:** 2026-04-08
- **Decision:** Audit log retention period is 90 days (default), configurable within range 30–365 days. Defined in config-index.md as `audit.retention_days`. Resolves OQ-003.
- **Affected Modules / Systems:** audit-logging
- **Status:** active
- **Superseded By:** —

---

## Decision Integrity Rules

- Every approved plan section MUST have a corresponding `DEC-NNN` entry
- Decisions are **NEVER** deleted — only superseded
- Superseded decisions MUST reference the original decision ID
- New decisions that replace existing ones MUST include a `superseded-by` link

## Enforcement Rule (CRITICAL)

- AI MUST read this document before any plan revision or execution
- If a proposed change conflicts with an active decision → the change is **INVALID** unless supersession is explicitly defined
- No decision may be ignored, bypassed, or implicitly overridden

## Traceability Requirement

All superseded decisions MUST maintain a traceable chain:
- Original decision → superseded-by → new decision
- Chains must remain intact for full historical reasoning

## Dependencies

- [Constitution](../00-governance/constitution.md) — Rule 8 (approved plan preservation)
- [Master Plan](master-plan.md)

## Used By / Affects

- AI Operating Model (mandatory reading step)
- All plan revisions
- All execution decisions

## Risks If Changed

HIGH — corruption of this document breaks memory, decision integrity, and system consistency.

## Related Documents

- [Master Plan](master-plan.md)
- [Plan Changelog](plan-changelog.md)

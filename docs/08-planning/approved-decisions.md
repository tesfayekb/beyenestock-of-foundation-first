# Approved Decisions

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Anti-forgetting ledger. Every approved plan section and decision is recorded here with a stable ID. Future plan revisions MUST preserve these unless explicitly superseded.

## Scope

All approved decisions across the project lifecycle.

## Decision Records

### DEC-001: SSOT Documentation System
- **Plan Section:** PLAN-GOV-001
- **Date Approved:** 2026-04-08
- **Decision:** Create a 42-file SSOT documentation system across 9 directories with full governance, plan preservation, stable IDs, execution lock, and merge rules.
- **Status:** Implemented
- **Superseded By:** —

### DEC-002: 10 Constitutional Rules
- **Plan Section:** PLAN-GOV-001
- **Date Approved:** 2026-04-08
- **Decision:** Constitution contains 10 non-negotiable rules including documentation phase lock, shared component protection, no silent behavior change, approved plan preservation, execution lock, and plan merge rule.
- **Status:** Active
- **Superseded By:** —

### DEC-003: Feature Scope Lock
- **Plan Section:** PLAN-GOV-001
- **Date Approved:** 2026-04-08
- **Decision:** Feature scope locked to: Authentication (email + social + MFA), RBAC (dynamic permissions), Admin panel + User panel, Audit logging + Health monitoring, API layer, Background jobs / scheduler. No scope expansion without explicit approval.
- **Status:** Active
- **Superseded By:** —

### DEC-004: Roles in Separate Table
- **Plan Section:** PLAN-RBAC-001
- **Date Approved:** 2026-04-08
- **Decision:** User roles MUST be stored in a separate `user_roles` table, never on the profile or users table. Security definer function `has_role()` used for all permission checks.
- **Status:** Active
- **Superseded By:** —

### DEC-005: Stable ID Convention
- **Plan Section:** PLAN-GOV-001
- **Date Approved:** 2026-04-08
- **Decision:** Plan sections use `PLAN-{MODULE}-{NNN}` format. Decisions use `DEC-{NNN}` format. IDs are permanent and never reassigned.
- **Status:** Active
- **Superseded By:** —

## Rules

- Every approved plan section gets a `DEC-NNN` entry here
- Entries are never deleted, only marked with `Superseded By`
- Future plan revisions must check this ledger before modifying any approved area
- If a decision is superseded, the new decision must reference the original `DEC-NNN`

## Dependencies

- [Constitution](../00-governance/constitution.md) — Rule 8 (approved plan preservation)
- [Master Plan](master-plan.md)

## Used By / Affects

AI Operating Model (mandatory reading step 3). All plan revisions.

## Related Documents

- [Master Plan](master-plan.md)
- [Plan Changelog](plan-changelog.md)

# Open Questions

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

## Purpose

Tracks unresolved questions separately from approved decisions.

This document controls uncertainty and prevents:
- Premature implementation
- Inconsistent decisions
- Implicit assumptions

## Scope

All open questions and pending decisions across the project.

## Enforcement Rule (CRITICAL)

- No implementation may proceed on any topic with an open question marked as **blocking**
- No assumptions may be made to resolve an open question
- If a change depends on an open question → the task must **STOP** until resolved
- Violations = **INVALID** change

## Open Questions

| ID | Question | Related Plan Section | Related Module | Impact | Owner | Raised Date | Status |
|----|----------|---------------------|---------------|--------|-------|-------------|--------|
| OQ-001 | Which OAuth providers beyond Google and Apple? | PLAN-AUTH-001 | auth | MEDIUM | Project Lead | 2026-04-08 | Resolved — DEC-020: Google + Apple only for v1. No additional OAuth providers. |
| OQ-002 | MFA recovery code format and count? | PLAN-AUTH-001 | auth | HIGH | Project Lead | 2026-04-08 | Resolved — DEC-017: 10 codes, 8 alphanumeric chars, single-use, regeneratable |
| OQ-003 | Audit log retention period? | PLAN-AUDIT-001 | audit-logging | MEDIUM | Project Lead | 2026-04-08 | Resolved — DEC-007: 90 days default (range 30–365), defined in config-index.md as `audit.retention_days` |
| OQ-004 | Include moderator role in v1? | PLAN-RBAC-001 | rbac | LOW | Project Lead | 2026-04-08 | Resolved — DEC-018: Moderator deferred to v2. V1 roles: superadmin, admin, user only. |
| OQ-005 | Job scheduling mechanism (pg_cron vs external)? | PLAN-JOBS-001 | jobs-and-scheduler | HIGH | Project Lead | 2026-04-08 | Resolved — DEC-019: pg_cron via Lovable Cloud. No external dependencies. |

## Impact Classification

| Level | Meaning |
|-------|---------|
| LOW | Does not block implementation |
| MEDIUM | May affect design decisions |
| HIGH | Blocks implementation until resolved |

## Resolution Workflow

When resolving a question:
1. Decision MUST be formally defined
2. Decision MUST be approved (via plan review)
3. A `DEC-NNN` entry MUST be created in `approved-decisions.md`
4. Related plan sections MUST be updated
5. This question MUST be marked as `Resolved` with reference to the decision ID

## Blocking Rule

- **HIGH** impact questions MUST be resolved before implementation
- **MEDIUM** questions must be reviewed before implementation
- **LOW** questions may proceed with documented assumptions (must be revisited)

## Escalation Rule

- Open questions must not remain unresolved indefinitely
- If a question persists across multiple plan revisions:
  - It must be escalated
  - Or explicitly deferred with rationale

## Dependencies

- [Master Plan](master-plan.md)

## Used By / Affects

- Planning decisions
- Execution eligibility
- Change control process

## Risks If Changed

HIGH — unresolved ambiguity leads to inconsistent implementation and system drift.

## Related Documents

- [Approved Decisions](approved-decisions.md)
- [Plan Review Log](plan-review-log.md)
- [Feature Proposals](feature-proposals.md)

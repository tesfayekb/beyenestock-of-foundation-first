# Risk Register

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Tracks identified project risks with mitigation strategies.

## Scope

Technical, security, and operational risks.

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Owner | Status |
|----|------|-----------|--------|-----------|-------|--------|
| RISK-001 | Privilege escalation via role manipulation | Low | Critical | Roles in separate table, security definer functions, RLS | Project Lead | Mitigated by design |
| RISK-002 | Context drift across AI sessions | Medium | High | SSOT system, mandatory reading order, plan governance | Project Lead | Mitigated by process |
| RISK-003 | Silent behavior change in shared functions | Medium | High | Function index, shared component protection rule | Project Lead | Mitigated by process |
| RISK-004 | Approved plan sections dropped in revisions | High | High | Plan preservation rule, stable IDs, merge rule, diff requirement | Project Lead | Mitigated by process |

## Rules

- New risks added when identified
- Each risk must have a mitigation strategy
- Risks are never deleted, only marked as `resolved` or `accepted`
- Review quarterly

## Dependencies

- [Constitution](../00-governance/constitution.md)

## Used By / Affects

Project planning, change control decisions.

## Risks If Changed

LOW — this is a tracking document.

## Related Documents

- [Regression Watchlist](regression-watchlist.md)
- [Constitution](../00-governance/constitution.md)
